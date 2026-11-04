"""Dossier documentaire (étape 11 du parcours).

**Pourquoi ce module existe.** UniOCR traitait des documents **un par un**. Le
parcours exige de regrouper plusieurs pièces (facture + connaissement + liste
de colisage), de savoir lesquelles manquent, où en est l'ensemble, et de
conserver l'historique.

**Ce qu'il fait.** Un dossier référence des documents déjà traités (par leur
`job_id`, jamais en recopiant leurs données), décrit les pièces attendues selon
un profil, calcule un état à partir de faits réels, et journalise chaque
ajout / retrait / changement d'état.

**Ce qu'il ne fait pas.** Il ne réinvente pas d'obligations réglementaires : les
profils décrivent des **pièces habituelles**, pas des exigences légales. Un
profil ne rend une pièce « requise » que parce que l'utilisateur l'a configuré
ainsi, et cette exigence reste modifiable.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .logging_setup import audit, get_logger

log = get_logger("dossier")

#: Champs restaurés par un traitement dédié dans `DossierStore._lire` ; les
#: autres champs du dataclass sont recopiés tels quels depuis le JSON.
CHAMPS_DOSSIER_SPECIAUX = frozenset({
    "id", "label", "profile", "state", "version", "created_at", "updated_at",
    "history", "arbitrages", "pieces",
})


class DossierState(str, Enum):
    """Les dix états exigés par le parcours."""
    EN_PREPARATION = "en_preparation"
    TRAITEMENT_EN_COURS = "traitement_en_cours"
    REVISION_REQUISE = "revision_requise"
    INCOMPLET = "incomplet"
    EN_VALIDATION = "en_validation"
    VALIDE = "valide"
    PRET_A_EXPORTER = "pret_a_exporter"
    EXPORTE = "exporte"
    ARCHIVE = "archive"
    ERREUR_TRAITEMENT = "erreur_traitement"


#: états qu'une relecture ne peut pas rétrograder : ils ont été posés par une
#: décision humaine explicite (forcer_etat). Le recalcul décrit l'avancement,
#: il ne défait pas une décision — sinon consulter un dossier archivé le
#: ferait revenir « incomplet » sans que personne n'ait rien demandé.
ETATS_VERROUILLES = frozenset({DossierState.EXPORTE, DossierState.ARCHIVE})

#: ordre de progression — utilisé pour empêcher un retour en arrière silencieux
ORDRE_ETATS = [
    DossierState.EN_PREPARATION,
    DossierState.INCOMPLET,
    DossierState.TRAITEMENT_EN_COURS,
    DossierState.REVISION_REQUISE,
    DossierState.EN_VALIDATION,
    DossierState.VALIDE,
    DossierState.PRET_A_EXPORTER,
    DossierState.EXPORTE,
    DossierState.ARCHIVE,
]

LIBELLES_ETATS = {
    DossierState.EN_PREPARATION: "En préparation",
    DossierState.TRAITEMENT_EN_COURS: "Traitement en cours",
    DossierState.REVISION_REQUISE: "Révision requise",
    DossierState.INCOMPLET: "Incomplet",
    DossierState.EN_VALIDATION: "En validation",
    DossierState.VALIDE: "Validé",
    DossierState.PRET_A_EXPORTER: "Prêt à exporter",
    DossierState.EXPORTE: "Exporté",
    DossierState.ARCHIVE: "Archivé",
    DossierState.ERREUR_TRAITEMENT: "Erreur de traitement",
}


@dataclass
class PieceAttendue:
    """Une pièce décrite par un profil.

    `required` est une **convention de dossier** choisie par l'utilisateur, pas
    une obligation réglementaire : le libellé le dit explicitement.
    """
    category: str
    label: str
    required: bool = False
    min_count: int = 1
    note: str = ""


@dataclass
class DossierProfile:
    id: str
    label: str
    description: str
    pieces: list[PieceAttendue] = field(default_factory=list)


#: Profils initiaux. Les pièces listées sont celles qu'on rencontre
#: habituellement dans ce type de dossier ; aucune n'est une exigence légale.
PROFILS_DOSSIER: dict[str, DossierProfile] = {
    "importation": DossierProfile(
        id="importation", label="Importation",
        description="Pièces habituelles d'un dossier d'importation (convention, "
                    "pas obligation réglementaire).",
        pieces=[
            PieceAttendue("invoice", "Facture commerciale", required=True),
            PieceAttendue("bill_of_lading", "Connaissement maritime", required=True),
            PieceAttendue("packing_list", "Liste de colisage"),
            PieceAttendue("certificate_of_origin", "Certificat d'origine"),
            PieceAttendue("customs_declaration", "Déclaration douanière"),
        ],
    ),
    "exportation": DossierProfile(
        id="exportation", label="Exportation",
        description="Pièces habituelles d'un dossier d'exportation (convention).",
        pieces=[
            PieceAttendue("invoice", "Facture commerciale", required=True),
            PieceAttendue("packing_list", "Liste de colisage", required=True),
            PieceAttendue("certificate_of_origin", "Certificat d'origine"),
            PieceAttendue("customs_declaration", "Déclaration douanière"),
        ],
    ),
    "transport": DossierProfile(
        id="transport", label="Transport",
        description="Pièces habituelles d'un dossier de transport (convention).",
        pieces=[
            PieceAttendue("bill_of_lading", "Connaissement maritime"),
            PieceAttendue("transport_document", "Document de transport"),
            PieceAttendue("packing_list", "Liste de colisage"),
        ],
    ),
    "conformite_documentaire": DossierProfile(
        id="conformite_documentaire", label="Conformité documentaire",
        description="Pièces habituelles d'un contrôle de conformité (convention).",
        pieces=[
            PieceAttendue("invoice", "Facture commerciale"),
            PieceAttendue("certificate_of_origin", "Certificat d'origine"),
            PieceAttendue("sanitary_certificate", "Certificat sanitaire"),
            PieceAttendue("phytosanitary_certificate", "Certificat phytosanitaire"),
            PieceAttendue("veterinary_certificate", "Certificat vétérinaire"),
        ],
    ),
    "personnalise": DossierProfile(
        id="personnalise", label="Personnalisé",
        description="Aucune pièce imposée : à décrire dans la configuration.",
        pieces=[],
    ),
}


@dataclass
class Piece:
    """Un document rattaché à un dossier (référence, pas copie)."""
    job_id: str
    filename: str
    category: str = "unknown"
    document_type: str = ""  # Type documentaire (facture, BL, etc.)
    document_category: str = ""  # Catégorie (client, commercial, maritime, douanier, sortie)
    added_at: float = field(default_factory=time.time)
    added_by: str = "systeme"
    sha256: str = ""
    note: str = ""
    source: str = ""  # Source du document (upload, OCR, import)
    page_count: int = 1  # Nombre de pages (pour les PDFs)
    mime_type: str = ""  # Type MIME du fichier
    file_size: int = 0  # Taille en octets
    ocr_engine: str = ""  # Moteur OCR utilisé
    ocr_confidence: float = 0.0  # Confiance OCR
    extracted_data: dict[str, Any] = field(default_factory=dict)  # Données extraites
    verification_status: str = "pending"  # Statut de vérification (pending, validated, rejected)
    validated_by: str = ""  # Validateur
    validation_date: float = 0.0  # Date de validation
    rejection_reason: str = ""  # Motif du rejet
    version: int = 1  # Version du document

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id, "filename": self.filename, "category": self.category,
            "document_type": self.document_type, "document_category": self.document_category,
            "added_at": self.added_at, "added_by": self.added_by, "sha256": self.sha256,
            "note": self.note, "source": self.source, "page_count": self.page_count,
            "mime_type": self.mime_type, "file_size": self.file_size,
            "ocr_engine": self.ocr_engine, "ocr_confidence": self.ocr_confidence,
            "extracted_data": self.extracted_data, "verification_status": self.verification_status,
            "validated_by": self.validated_by, "validation_date": self.validation_date,
            "rejection_reason": self.rejection_reason, "version": self.version,
        }


@dataclass
class Evenement:
    ts: float
    action: str
    detail: dict[str, Any] = field(default_factory=dict)
    acteur: str = "systeme"

    def as_dict(self) -> dict[str, Any]:
        return {"ts": self.ts, "action": self.action,
                "detail": self.detail, "acteur": self.acteur}


@dataclass
class Dossier:
    id: str
    label: str
    profile: str = "personnalise"
    state: DossierState = DossierState.EN_PREPARATION
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    history: list[Evenement] = field(default_factory=list)
    #: pièces déjà traitées rattachées au dossier (référencées par `job_id`).
    pieces: list[Piece] = field(default_factory=list)
    #: arbitrages humains des constats de cohérence, indexés par règle. Les
    #: constats sont recalculés à chaque lecture : sans cette mémoire, une
    #: divergence tranchée par un humain réapparaîtrait « à trancher » au
    #: rechargement suivant, et sa décision serait perdue.
    arbitrages: dict[str, dict] = field(default_factory=dict)
    # ─────────────────────────── informations maritimes ───────────────────────────

    reference: str = ""
    type_operation: str = ""
    client_importateur: str = ""
    fournisseur: str = ""
    pays_origine: str = ""
    pays_expedition: str = ""
    port_chargement: str = ""
    port_destination: str = ""
    navire: str = ""
    numero_voyage: str = ""
    eta: str = ""
    eta_effective: str = ""
    reference_bl: str = ""
    incoterm: str = ""
    lieu_incoterm: str = ""
    numero_conteneur: str = ""
    numero_scelle: str = ""
    type_conteneur: str = ""
    poids: float = 0.0
    statut_documentaire: str = ""
    statut_enlèvement: str = ""
    echeances: list[dict[str, Any]] = field(default_factory=list)
    frais_associes: float = 0.0

    # ─────────────────────── valeur commerciale & marchandise ───────────────────
    # Ces champs sont exposés par `as_dict()` et alimentent l'UI ; ils doivent
    # donc exister sur le dataclass (leur absence faisait échouer toute lecture
    # de dossier en 500).
    devise: str = "EUR"
    valeur_commerciale: float = 0.0
    nombre_colis: int = 0
    poids_brut: float = 0.0
    poids_net: float = 0.0
    description_marchandise: str = ""
    code_sh: str = ""
    conteneurs_associes: list[str] = field(default_factory=list)
    gestionnaire: str = ""
    date_ouverture: float = 0.0
    dernier_etat_evolution: str = ""
    priorite: str = "normale"

    frais_de_fret: float = 0.0
    frais_transport_terrestre: float = 0.0
    frais_portuaires: float = 0.0
    frais_manutention: float = 0.0
    frais_magasinage: float = 0.0
    frais_surestaries: float = 0.0
    frais_detention: float = 0.0
    droits_douane: float = 0.0
    tva: float = 0.0
    tpc: float = 0.0
    autres_frais: float = 0.0
    devise_frais: str = "EUR"
    reference_facture: str = ""
    date_dernier_paiement: float = field(default_factory=time.time)
    statut_paiement: str = "non_paye"
    commentaire: str = ""
    observations: str = ""

    # ─────────────────────────── dérivés ───────────────────────────

    def job_ids(self) -> list[str]:
        return [p.job_id for p in self.pieces]

    def categories(self) -> dict[str, int]:
        compte: dict[str, int] = {}
        for p in self.pieces:
            compte[p.category] = compte.get(p.category, 0) + 1
        return compte

    def piece_par_job(self, job_id: str) -> Optional[Piece]:
        for p in self.pieces:
            if p.job_id == job_id:
                return p
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "label": self.label, "profile": self.profile,
            "state": self.state.value, "state_label": LIBELLES_ETATS[self.state],
            "reference": self.reference,
            "type_operation": self.type_operation,
            "client_importateur": self.client_importateur,
            "fournisseur": self.fournisseur,
            "pays_origine": self.pays_origine,
            "pays_expedition": self.pays_expedition,
            "port_chargement": self.port_chargement,
            "port_destination": self.port_destination,
            "navire": self.navire,
            "numero_voyage": self.numero_voyage,
            "eta": self.eta,
            "eta_effective": self.eta_effective,
            "reference_bl": self.reference_bl,
            "incoterm": self.incoterm,
            "lieu_incoterm": self.lieu_incoterm,
            "devise": self.devise,
            "valeur_commerciale": self.valeur_commerciale,
            "nombre_colis": self.nombre_colis,
            "poids_brut": self.poids_brut,
            "poids_net": self.poids_net,
            "description_marchandise": self.description_marchandise,
            "code_sh": self.code_sh,
            "conteneurs_associes": self.conteneurs_associes,
            "gestionnaire": self.gestionnaire,
            "date_ouverture": self.date_ouverture,
            "dernier_etat_evolution": self.dernier_etat_evolution,
            "echeances": self.echeances,
            "priorite": self.priorite,
            "observations": self.observations,
            "pieces": [p.as_dict() for p in self.pieces],
            "categories": self.categories(),
            "version": self.version,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "history": [e.as_dict() for e in self.history],
            "arbitrages": dict(self.arbitrages),
        }


class DossierStore:
    """Persistance JSON des dossiers, sous `data/dossiers/`."""

    #: Labels d'affichage pour les états
    _LABELS_ETATS = {
        DossierState.EN_PREPARATION: "En préparation",
        DossierState.TRAITEMENT_EN_COURS: "Traitement en cours",
        DossierState.REVISION_REQUISE: "Révision requise",
        DossierState.INCOMPLET: "Incomplet",
        DossierState.EN_VALIDATION: "En validation",
        DossierState.VALIDE: "Validé",
        DossierState.PRET_A_EXPORTER: "Prêt à exporter",
        DossierState.EXPORTE: "Exporté",
        DossierState.ARCHIVE: "Archivé",
        DossierState.ERREUR_TRAITEMENT: "Erreur de traitement",
    }

    def __init__(self, root: Path, log_dir: Optional[Path] = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_dir = log_dir or self.root.parent / "logs"
        self._cache: dict[str, Dossier] = {}

    # ─────────────────────────── persistance ───────────────────────────

    def _chemin(self, dossier_id: str) -> Path:
        return self.root / f"{dossier_id}.json"

    def _lire(self, dossier_id: str) -> Optional[Dossier]:
        if dossier_id in self._cache:
            return self._cache[dossier_id]
        p = self._chemin(dossier_id)
        if not p.is_file():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            log.error("dossier illisible (%s) : %s", p.name, exc)
            return None
        # Tous les champs métier (informations maritimes, valeur commerciale,
        # frais, priorité…) doivent survivre à un rechargement : on les recopie
        # génériquement pour qu'aucun ajout de champ n'exige de retoucher ici.
        champs_metier = {
            nom: valeur for nom, valeur in data.items()
            if nom in Dossier.__dataclass_fields__
            and nom not in CHAMPS_DOSSIER_SPECIAUX
        }
        dossier = Dossier(
            id=data["id"], label=data.get("label", ""),
            profile=data.get("profile", "personnalise"),
            state=DossierState(data.get("state", "en_preparation")),
            version=int(data.get("version", 1)),
            created_at=float(data.get("created_at", time.time())),
            updated_at=float(data.get("updated_at", time.time())),
            history=[Evenement(**{k: v for k, v in e.items()
                                if k in Evenement.__dataclass_fields__})
                    for e in data.get("history", [])],
            arbitrages={k: v for k, v in (data.get("arbitrages") or {}).items()
                        if isinstance(v, dict)},
            **champs_metier,
        )
        dossier.pieces = [Piece(**{k: v for k, v in piece.items()
                                    if k in Piece.__dataclass_fields__})
                          for piece in data.get("pieces", [])]
        self._cache[dossier_id] = dossier
        return dossier

    def _ecrire(self, dossier: Dossier) -> None:
        dossier.updated_at = time.time()
        tmp = self._chemin(dossier.id).with_suffix(".tmp")
        tmp.write_text(json.dumps(dossier.as_dict(), ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(self._chemin(dossier.id))
        self._cache[dossier.id] = dossier

    def _journalise(self, dossier: Dossier, action: str, detail: dict,
                    acteur: str = "systeme") -> None:
        dossier.history.append(Evenement(ts=time.time(), action=action,
                                         detail=detail, acteur=acteur))
        # l'historique garde tout, mais on évite qu'il enfle sans limite
        if len(dossier.history) > 500:
            dossier.history = dossier.history[-500:]
        audit(self.log_dir, f"dossier_{action}", dossier_id=dossier.id,
              acteur=acteur, **detail)

    # ─────────────────────────── cycle de vie ───────────────────────────

    def journaliser(self, dossier_id: str, action: str, detail: dict,
                    acteur: str = "systeme") -> None:
        """Journalise un fait sur un dossier — porte d'entrée publique.

        `_journalise` reste privé parce qu'il travaille sur un dossier déjà
        chargé. Un module voireisin (transmission, archivage) n'a qu'un
        identifiant : cette méthode lui évite de passer par le privé, et
        garantit que l'événement porte bien le préfixe `dossier_`.
        """
        dossier = self._lire(dossier_id)
        if dossier is None:
            raise KeyError(f"dossier introuvable : {dossier_id}")
        self._journalise(dossier, action, dict(detail or {}), acteur)
        self._ecrire(dossier)

    def creer(self, label: str, profile: str = "personnalise",
              acteur: str = "systeme") -> Dossier:
        if profile not in PROFILS_DOSSIER:
            raise ValueError(f"profil de dossier inconnu : {profile}")
        dossier = Dossier(id=self._nouvel_id(), label=label, profile=profile)
        self._journalise(dossier, "created", {"profile": profile}, acteur)
        self._ecrire(dossier)
        return dossier

    @staticmethod
    def _nouvel_id() -> str:
        import secrets
        return "dos_" + secrets.token_hex(6)

    def get(self, dossier_id: str) -> Optional[Dossier]:
        return self._lire(dossier_id)

    def mettre_a_jour(self, dossier_id: str, champs: dict[str, Any],
                      acteur: str = "systeme") -> Optional[Dossier]:
        """Applique des champs métier à un dossier et persiste le résultat.

        Seuls les champs du dataclass sont acceptés : une clé inconnue est
        ignorée plutôt que de faire échouer la requête entière (les clients
        envoient parfois des champs d'affichage comme `state_label`).
        """
        dossier = self._lire(dossier_id)
        if dossier is None:
            return None
        modifies = {
            nom: valeur for nom, valeur in champs.items()
            if nom in Dossier.__dataclass_fields__
            and nom not in CHAMPS_DOSSIER_SPECIAUX
        }
        if modifies:
            for nom, valeur in modifies.items():
                setattr(dossier, nom, valeur)
            self._journalise(dossier, "mise_a_jour", modifies, acteur)
            self._ecrire(dossier)
        return dossier

    # ── vue « dictionnaire » utilisée par le module transit ──────────

    def get_dossier(self, dossier_id: str) -> Optional[dict[str, Any]]:
        """Dossier sous forme de dictionnaire (lecture seule)."""
        dossier = self.get(dossier_id)
        return dossier.as_dict() if dossier else None

    def list_dossiers(self) -> list[dict[str, Any]]:
        """Tous les dossiers sous forme de dictionnaires."""
        return [d.as_dict() for d in self.liste()]

    def save_dossier(self, dossier_id: str, champs: dict[str, Any],
                     acteur: str = "systeme") -> Optional[dict[str, Any]]:
        """Enregistre les champs connus d'un dossier ; les autres sont ignorés."""
        dossier = self.mettre_a_jour(dossier_id, champs, acteur=acteur)
        return dossier.as_dict() if dossier else None

    def update_dossier(self, dossier_id: str, champs: dict[str, Any],
                       acteur: str = "systeme") -> Optional[dict[str, Any]]:
        """Alias historique de :meth:`save_dossier`."""
        return self.save_dossier(dossier_id, champs, acteur=acteur)

    def liste(self) -> list[Dossier]:
        dossiers = []
        for p in sorted(self.root.glob("*.json")):
            d = self._lire(p.stem)
            if d:
                dossiers.append(d)
        dossiers.sort(key=lambda d: d.updated_at, reverse=True)
        return dossiers

    def supprimer(self, dossier_id: str, acteur: str = "systeme") -> bool:
        """Supprime le dossier — **pas** les documents, qui restent en place."""
        dossier = self._lire(dossier_id)
        if not dossier:
            return False
        self._journalise(dossier, "deleted",
                         {"pieces": len(dossier.pieces)}, acteur)
        self._chemin(dossier_id).unlink(missing_ok=True)
        self._cache.pop(dossier_id, None)
        return True

# ─────────────────────────── conteneurs ───────────────────────────

    # ─────────────────────────── pièces ───────────────────────────

    def ajouter_piece(self, dossier_id: str, job_id: str, filename: str,
                      category: str = "unknown", sha256: str = "",
                      acteur: str = "systeme", note: str = "") -> Dossier:
        dossier = self._lire(dossier_id)
        if not dossier:
            raise KeyError(f"dossier introuvable : {dossier_id}")
        existante = dossier.piece_par_job(job_id)
        if existante:
            # pas de doublon silencieux : on met à jour la catégorie si besoin
            if category != "unknown" and existante.category == "unknown":
                existante.category = category
                self._journalise(dossier, "piece_recategorized",
                                 {"job_id": job_id, "category": category}, acteur)
            return self._ecrire(dossier) or dossier

        dossier.pieces.append(Piece(job_id=job_id, filename=filename,
                                    category=category, sha256=sha256,
                                    added_by=acteur, note=note))
        self._journalise(dossier, "piece_added",
                         {"job_id": job_id, "filename": filename,
                          "category": category}, acteur)
        self._ecrire(dossier)
        return dossier

    def retirer_piece(self, dossier_id: str, job_id: str,
                      acteur: str = "systeme", motif: str = "") -> Dossier:
        """Retrait contrôlé : la pièce est conservée dans l'historique."""
        dossier = self._lire(dossier_id)
        if not dossier:
            raise KeyError(f"dossier introuvable : {dossier_id}")
        piece = dossier.piece_par_job(job_id)
        if not piece:
            raise KeyError(f"pièce absente du dossier : {job_id}")
        dossier.pieces = [p for p in dossier.pieces if p.job_id != job_id]
        self._journalise(dossier, "piece_removed",
                         {"job_id": job_id, "filename": piece.filename,
                          "motif": motif}, acteur)
        self._ecrire(dossier)
        return dossier

    # ─────────────────────── pièces manquantes ───────────────────────

    def pieces_manquantes(self, dossier: Dossier, include_verified: bool = True) -> list[dict[str, Any]]:
        """Pièces attendues par le profil et absentes du dossier."""
        profil = PROFILS_DOSSIER.get(dossier.profile)
        if not profil:
            return []
        presentes = dossier.categories()
        manquantes = []
        for attendue in profil.pieces:
            nb = presentes.get(attendue.category, 0)
            if nb < attendue.min_count:
                manquantes.append({
                    "category": attendue.category, "label": attendue.label,
                    "required": attendue.required,
                    "expected": attendue.min_count, "present": nb,
                    "note": attendue.note,
                })
        # Ajouter les pièces non détectées si requesté
        if include_verified:
            for piece in dossier.pieces:
                if piece.document_category and not any(
                    m["category"] == piece.document_category for m in manquantes
                ):
                    manquantes.append({
                        "category": piece.document_category, "label": piece.document_type or piece.category,
                        "required": False, "expected": 1, "present": 1,
                        "note": "Pièce détectée mais non configurée dans le profil",
                    })
        return manquantes

    # ─────────────────────────── état ───────────────────────────

    def recalculer_etat(self, dossier_id: str,
                        etats_documents: dict[str, dict[str, Any]]) -> Dossier:
        """Calcule l'état du dossier à partir de faits réels.

        `etats_documents` décrit chaque pièce :
        `{"status": "done|processing|queued|failed", "needs_review": bool,
        "valide": bool}`. L'état n'est **jamais** posé par un bouton : il est
        déduit. Un dossier déjà exporté ou archivé n'est pas rétrogradé sans
        décision explicite (`forcer_etat`).
        """
        dossier = self._lire(dossier_id)
        if not dossier:
            raise KeyError(f"dossier introuvable : {dossier_id}")

        manquantes = self.pieces_manquantes(dossier)
        requises_manquantes = [m for m in manquantes if m["required"]]

        etats = [etats_documents.get(p.job_id, {}) for p in dossier.pieces]
        en_cours = any(e.get("status") in ("processing", "queued") for e in etats)
        en_erreur = any(e.get("status") == "failed" for e in etats)
        a_revoir = any(e.get("needs_review") for e in etats)
        tous_valides = bool(etats) and all(e.get("valide") for e in etats)

        if en_erreur:
            nouvel = DossierState.ERREUR_TRAITEMENT
        elif not dossier.pieces:
            nouvel = DossierState.EN_PREPARATION
        elif en_cours:
            nouvel = DossierState.TRAITEMENT_EN_COURS
        elif a_revoir:
            nouvel = DossierState.REVISION_REQUISE
        elif requises_manquantes:
            nouvel = DossierState.INCOMPLET
        elif tous_valides:
            nouvel = DossierState.VALIDE
        else:
            nouvel = DossierState.EN_VALIDATION

        # Un dossier exporté ou archivé n'est pas rétrogradé par une simple
        # relecture : le recalcul décrit l'avancement, il ne défait pas une
        # décision humaine explicite. Sans cette garde, afficher un dossier
        # archivé le faisait silencieusement revenir « incomplet ».
        if dossier.state in ETATS_VERROUILLES:
            return dossier

        if nouvel != dossier.state:
            self._journalise(dossier, "state_changed",
                             {"from": dossier.state.value, "to": nouvel.value,
                              "pieces": len(dossier.pieces)})
            dossier.state = nouvel
        self._ecrire(dossier)
        return dossier

    def forcer_etat(self, dossier_id: str, etat: DossierState,
                    acteur: str = "systeme", motif: str = "") -> Dossier:
        """Changement d'état explicite (export, archivage) — tracé et motivé."""
        dossier = self._lire(dossier_id)
        if not dossier:
            raise KeyError(f"dossier introuvable : {dossier_id}")
        if etat != dossier.state:
            self._journalise(dossier, "state_forced",
                             {"from": dossier.state.value, "to": etat.value,
                              "motif": motif}, acteur)
            dossier.state = etat
            dossier.version += 1
        self._ecrire(dossier)
        return dossier

    def trancher_constat(self, dossier_id: str, regle: str, statut: str,
                         acteur: str = "utilisateur", motif: str = "") -> Dossier:
        """Enregistre l'arbitrage humain d'un constat de coherence.

        La decision est memorisee par regle puis reappliquee aux constats
        recalcules. Elle n'ecrase aucun document : la valeur d'origine et
        l'ecart restent lisibles, seule la main de l'humain s'ajoute.
        """
        dossier = self._lire(dossier_id)
        if not dossier:
            raise KeyError(f"dossier introuvable : {dossier_id}")
        precedent = dossier.arbitrages.get(regle)
        dossier.arbitrages[regle] = {
            "rule": regle, "status": statut, "acteur": acteur,
            "motif": motif, "ts": time.time(),
            "remplace": (precedent or {}).get("status"),
        }
        dossier.version += 1
        self._journalise(dossier, "constat_tranche",
                         {"rule": regle, "status": statut, "motif": motif,
                          "precedent": (precedent or {}).get("status")},
                         acteur)
        self._ecrire(dossier)
        return dossier

    # ─────────────────────── synthese ───────────────────────

    def synthese(self, dossier: Dossier,
                 donnees: Optional[dict[str, dict[str, Any]]] = None) -> dict[str, Any]:
        """Résumé du dossier : pièces, catégories, manquants, état, historique.

        `donnees` peut porter les champs extraits par document
        (`{job_id: {champ: valeur}}`) pour alimenter le résumé ; sans eux, le
        résumé reste structurel (pas de valeurs inventées).
        """
        donnees = donnees or {}
        manquantes = self.pieces_manquantes(dossier)
        return {
            "id": dossier.id, "label": dossier.label,
            "profile": dossier.profile,
            "profile_label": PROFILS_DOSSIER[dossier.profile].label
            if dossier.profile in PROFILS_DOSSIER else dossier.profile,
            "state": dossier.state.value,
            "state_label": LIBELLES_ETATS[dossier.state],
            "version": dossier.version,
            "pieces": [p.as_dict() for p in dossier.pieces],
            "categories": dossier.categories(),
            "pieces_manquantes": manquantes,
            "requises_manquantes": [m for m in manquantes if m["required"]],
            "champs_par_document": donnees,
            "history_tail": [e.as_dict() for e in dossier.history[-20:]],
        }

class Conteneur:
    """Fiche de suivi d'un conteneur associé à un dossier."""
    def __init__(self, reference: str, type_conteneur: str = "",
                 poids: float = 0.0, scelle: str = "",
                 statut_documentaire: str = "",
                 statut_enlèvement: str = "",
                 gestionnaire: str = "") -> None:
        self.reference = reference
        self.type_conteneur = type_conteneur
        self.poids = poids
        self.scelle = scelle
        self.statut_documentaire = statut_documentaire
        self.statut_enlèvement = statut_enlèvement
        self.gestionnaire = gestionnaire
        self.date_creation = time.time()
        self.historique: list[dict[str, Any]] = []
        self.date_enlèvement: float | None = None
        self.date_restitution: float | None = None
        self.anomalies: list[dict[str, Any]] = []

    def associer_au_dossier(self, dossier_id: str, acteur: str = "systeme") -> None:
        """Lier ce conteneur à un dossier."""
        self.historique.append({
            "action": "association_au_dossier",
            "dossier_id": dossier_id,
            "acteur": acteur,
            "date": time.time(),
        })

    def detacher_du_dossier(self, dossier_id: str, acteur: str = "systeme") -> None:
        """Dissocier ce conteneur du dossier."""
        self.historique.append({
            "action": "detachement_du_dossier",
            "dossier_id": dossier_id,
            "acteur": acteur,
            "date": time.time(),
        })

    def marquer_enlèvement(self, date: float, acteur: str = "systeme") -> None:
        """Marquer l'enlèvement du conteneur."""
        self.date_enlèvement = date
        self.historique.append({
            "action": "enlèvement",
            "date": date,
            "acteur": acteur,
        })

    def marquer_restitution(self, date: float, acteur: str = "systeme") -> None:
        """Marquer la restitution du conteneur."""
        self.date_restitution = date
        self.historique.append({
            "action": "restitution",
            "date": date,
            "acteur": acteur,
        })

    def ajouter_anomalie(self, description: str, detail: dict[str, Any] | None = None, acteur: str = "systeme") -> None:
        """Ajouter une anomalie au conteneur."""
        self.anomalies.append({
            "action": "anomalie",
            "description": description,
            "detail": detail or {},
            "acteur": acteur,
            "date": time.time(),
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference,
            "type_conteneur": self.type_conteneur,
            "poids": self.poids,
            "scelle": self.scelle,
            "statut_documentaire": self.statut_documentaire,
            "statut_enlèvement": self.statut_enlèvement,
            "gestionnaire": self.gestionnaire,
            "date_creation": self.date_creation,
            "date_enlèvement": self.date_enlèvement,
            "date_restitution": self.date_restitution,
            "anomalies": self.anomalies,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Conteneur":
        c = Conteneur(
            reference=data.get("reference", ""),
            type_conteneur=data.get("type_conteneur", ""),
            poids=data.get("poids", 0.0),
            scelle=data.get("scelle", ""),
            statut_documentaire=data.get("statut_documentaire", ""),
            statut_enlèvement=data.get("statut_enlèvement", ""),
            gestionnaire=data.get("gestionnaire", ""),
        )
        c.date_creation = data.get("date_creation", time.time())
        c.date_enlèvement = data.get("date_enlèvement")
        c.date_restitution = data.get("date_restitution")
        c.anomalies = data.get("anomalies", [])
        return c
