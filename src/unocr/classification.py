"""Classification documentaire (étape 4 du parcours).

**Pourquoi ce module existe.** Aucun classifieur n'existait : le profil
d'extraction était choisi *par l'utilisateur* (`--profile`), donc un document
déposé sans profil était traité avec le profil générique. Le parcours exige
d'identifier le type du document, avec une confiance, des indices, et une file
de révision pour les cas incertains.

**Ce qu'il fait.** Il note chaque catégorie sur des **indices textuels
explicites** (expressions régulières pondérées) et renvoie le type, la
confiance, les indices qui ont matché, les alternatives et la nécessité de
révision. Les catégories couvertes par un profil d'extraction existant
(`invoice`, `port_bl`, `packing_list`…) héritent automatiquement des motifs de
ce profil : pas de deuxième définition des mêmes champs.

**Ce qu'il ne fait pas.** Il n'invente pas de pourcentage : la confiance est la
couverture pondérée des indices réellement matchés, plafonnée à 0,95 — un
classifieur n'est jamais certain. Une catégorie **sans indice configuré ne peut
pas être proposée** : elle est déclarée mais désactivée, et son absence est
visible (`disabled_categories`) plutôt que masquée par un repli silencieux.

**Ne jamais forcer un document dans une catégorie.** Sous le seuil, le résultat
est `unknown` avec `needs_review=True`, jamais la catégorie la plus proche.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from .logging_setup import audit, get_logger

log = get_logger("classification")

#: version du classifieur — tracée avec chaque résultat, pour pouvoir
#: distinguer « le document a changé » de « le classifieur a changé ».
CLASSIFIER_VERSION = "1.0.0"

#: confiance à partir de laquelle une classification est proposée sans révision
SEUIL_ACCEPTATION = 0.70
#: en dessous, le document part en révision (mais reste proposé si > 0)
SEUIL_REVISION = 0.40
#: écart maximal entre les deux meilleures catégories pour rester « sûr »
MARGE_AMBIGUITE = 0.12
#: absorption de la fonction de confiance : confiance = obtenu / (obtenu + k).
#: Un indice distinctif isolé (poids 3) donne 3 / 4,2 ≈ 0,71 — assez pour
#: proposer, pas assez pour être sûr. Deux indices forts donnent ≈ 0,81.
ABSORPTION = 1.2
#: plafond absolu : un classifieur n'est jamais certain à 100 %
CONFIANCE_MAX = 0.95


@dataclass
class Indicateur:
    """Un indice textuel : un motif, son poids et son libellé affichable."""
    motif: str
    poids: float = 1.0
    libelle: str = ""

    def compile(self) -> re.Pattern:
        return re.compile(self.motif, re.IGNORECASE)


@dataclass
class Categorie:
    """Catégorie documentaire et ses indices.

    `source` dit d'où viennent les indices : `profile:<nom>` quand ils sont
    dérivés d'un profil d'extraction existant, `builtin` pour les catégories
    intégrées, `user:<fichier>` pour une catégorie ajoutée par l'utilisateur.
    """
    id: str
    label: str
    indicateurs: list[Indicateur] = field(default_factory=list)
    source: str = "builtin"
    active: bool = True          # False = déclarée mais sans indice exploitable
    profil: Optional[str] = None  # profil d'extraction à appliquer si confirmé

    def poids_total(self) -> float:
        return sum(i.poids for i in self.indicateurs) or 1.0

    def poids_principal(self) -> float:
        """Poids des indices **distinctifs** (poids >= 1).

        Les indices hérités des profils d'extraction (poids 0,5) sont nombreux
        et peu discriminants : les compter au dénominateur diluerait la
        confiance d'un document pourtant reconnu. Ils servent de preuves
        complémentaires, pas de base de calcul.
        """
        return sum(i.poids for i in self.indicateurs if i.poids >= 1.0)


@dataclass
class ClassificationResult:
    """Résultat de classification — sérialisable, traçable, honnête."""
    category: str
    label: str
    confidence: float
    evidence: list[dict[str, Any]] = field(default_factory=list)
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    classifier_version: str = CLASSIFIER_VERSION
    needs_review: bool = False
    reason: str = ""
    manual: bool = False            # True si posé par un humain
    corrected_by: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "label": self.label,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
            "alternatives": self.alternatives,
            "classifier_version": self.classifier_version,
            "needs_review": self.needs_review,
            "reason": self.reason,
            "manual": self.manual,
            "corrected_by": self.corrected_by,
        }


# ─────────────────────────── catégories intégrées ────────────────────────────
# Les indices sont volontairement **distinctifs** : un motif présent dans
# plusieurs catégories ferait basculer un document au hasard. Quand deux
# catégories se recoupent (connaissement / document de transport / bon de
# livraison), l'indice le plus spécifique est celui qui tranche.

_BUILTIN: list[Categorie] = [
    Categorie(
        id="invoice", label="Facture commerciale",
        source="profile:invoice", profil="invoice",
        indicateurs=[
            Indicateur(r"\bINVOICE\b", 2.0, "mot INVOICE"),
            Indicateur(r"\bFACTURE\b", 2.0, "mot FACTURE"),
            Indicateur(r"(?:Invoice|Facture)\s*(?:No|N[°o]|Number|Num[ée]ro)", 1.5, "numéro de facture"),
            Indicateur(r"\b(?:NET|GROSS|TOTAL)\s+(?:AMOUNT|TOTAL|HT|TTC)\b", 1.0, "montant total"),
            Indicateur(r"\bINCO?TERMS?\b", 1.0, "Incoterm"),
        ],
    ),
    Categorie(
        id="bill_of_lading", label="Connaissement maritime",
        source="profile:port_bl", profil="port_bl",
        indicateurs=[
            Indicateur(r"BILL\s*OF\s*LADING", 3.0, "mot BILL OF LADING"),
            Indicateur(r"\bB/?L\s*(?:No|N[°o]|Number)", 2.0, "numéro de BL"),
            Indicateur(r"\bSHIPPER\b", 1.5, "chargeur"),
            Indicateur(r"\bCONSIGNEE\b", 1.5, "destinataire"),
            Indicateur(r"\bNOTIFY\s*PARTY\b", 1.5, "notify party"),
            Indicateur(r"\b(?:PORT\s*OF\s*LOADING|PORT\s*OF\s*DISCHARGE)\b", 1.5, "ports"),
            Indicateur(r"\b(?:VOYAGE|VESSEL)\b", 1.0, "navire/voyage"),
        ],
    ),
    Categorie(
        id="packing_list", label="Liste de colisage",
        source="profile:packing_list", profil="packing_list",
        indicateurs=[
            Indicateur(r"PACKING\s*(?:LIST|SLIP)", 3.0, "mot PACKING LIST"),
            Indicateur(r"LISTE\s*DE\s*COLISAGE", 3.0, "mot LISTE DE COLISAGE"),
            Indicateur(r"\b(?:GROSS|NET)\s*WEIGHT\b", 1.0, "poids"),
            Indicateur(r"\b(?:CARTONS?|COLIS|PACKAGES?)\b", 1.0, "colis"),
        ],
    ),
    Categorie(
        id="certificate_of_origin", label="Certificat d'origine",
        indicateurs=[
            Indicateur(r"CERTIFICATE\s*OF\s*ORIGIN", 3.0, "mot CERTIFICATE OF ORIGIN"),
            Indicateur(r"CERTIFICAT\s*D['’]?\s*ORIGINE", 3.0, "mot CERTIFICAT D'ORIGINE"),
            Indicateur(r"\bCOUNTRY\s*OF\s*ORIGIN\b", 1.5, "pays d'origine"),
        ],
    ),
    Categorie(
        id="transport_document", label="Document de transport",
        indicateurs=[
            Indicateur(r"\bCMR\b", 2.5, "mot CMR"),
            Indicateur(r"AIR\s*WAYBILL", 2.5, "mot AIR WAYBILL"),
            Indicateur(r"\bAWB\b", 2.0, "mot AWB"),
            Indicateur(r"LETTRE\s*DE\s*TRANSPORT", 2.5, "mot LETTRE DE TRANSPORT"),
            Indicateur(r"\b(?:ROAD|RAIL)\s*CONSIGNMENT\s*NOTE\b", 2.0, "note de transport"),
        ],
    ),
    Categorie(
        id="customs_declaration", label="Déclaration douanière",
        indicateurs=[
            Indicateur(r"(?:D[ÉE]CLARATION\s*EN\s*DOUANE|CUSTOMS\s*DECLARATION)", 3.0, "mot déclaration en douane"),
            Indicateur(r"\bSAD\b", 2.0, "mot SAD"),
            Indicateur(r"\b(?:HS\s*CODE|CODE\s*(?:SH|TARIC))\b", 1.5, "code SH"),
            Indicateur(r"\bR[ÉE]GIME\s*(?:DOUANIER|CUSTOMS)\b", 1.5, "régime"),
        ],
    ),
    Categorie(
        id="receipt", label="Quittance",
        indicateurs=[
            Indicateur(r"\bQUITTANCE\b", 2.5, "mot QUITTANCE"),
            Indicateur(r"\bRE[ÇC]U\b", 2.0, "mot REÇU"),
            Indicateur(r"\bRECEIPT\b", 2.0, "mot RECEIPT"),
            Indicateur(r"\bPAID\s*IN\s*FULL\b", 1.0, "acquitté"),
        ],
    ),
    Categorie(
        id="administrative_authorization", label="Autorisation administrative",
        indicateurs=[
            Indicateur(r"\bAUTORISATION\b", 2.0, "mot AUTORISATION"),
            Indicateur(r"\bAUTHORIZATION\b", 2.0, "mot AUTHORIZATION"),
            Indicateur(r"\b(?:LICENCE|LICENSE)\b", 1.5, "licence"),
            Indicateur(r"\bAGR[ÉE]MENT\b", 2.0, "agrément"),
        ],
    ),
    Categorie(
        id="sanitary_certificate", label="Certificat sanitaire",
        indicateurs=[
            Indicateur(r"SANITARY\s*CERTIFICATE", 3.0, "mot SANITARY CERTIFICATE"),
            Indicateur(r"CERTIFICAT\s*SANITAIRE", 3.0, "mot CERTIFICAT SANITAIRE"),
        ],
    ),
    Categorie(
        id="phytosanitary_certificate", label="Certificat phytosanitaire",
        indicateurs=[
            Indicateur(r"PHYTOSANITARY\s*CERTIFICATE", 3.0, "mot PHYTOSANITARY CERTIFICATE"),
            Indicateur(r"CERTIFICAT\s*PHYTOSANITAIRE", 3.0, "mot CERTIFICAT PHYTOSANITAIRE"),
            Indicateur(r"\bIPPC\b", 1.0, "marque IPPC"),
        ],
    ),
    Categorie(
        id="veterinary_certificate", label="Certificat vétérinaire",
        indicateurs=[
            Indicateur(r"VETERINARY\s*CERTIFICATE", 3.0, "mot VETERINARY CERTIFICATE"),
            Indicateur(r"CERTIFICAT\s*V[ÉE]T[ÉE]RINAIRE", 3.0, "mot CERTIFICAT VÉTÉRINAIRE"),
        ],
    ),
    Categorie(
        id="delivery_order", label="Bon à délivrer",
        indicateurs=[
            Indicateur(r"BON\s*[ÀA]\s*D[ÉE]LIVRER", 3.0, "mot BON À DÉLIVRER"),
            Indicateur(r"DELIVERY\s*ORDER", 3.0, "mot DELIVERY ORDER"),
        ],
    ),
    Categorie(
        id="delivery_note", label="Bon de livraison",
        indicateurs=[
            Indicateur(r"BON\s*DE\s*LIVRAISON", 3.0, "mot BON DE LIVRAISON"),
            Indicateur(r"DELIVERY\s*NOTE", 3.0, "mot DELIVERY NOTE"),
            Indicateur(r"\bB\.?L\.?\s*(?:DE\s*)?LIVRAISON\b", 2.0, "BL de livraison"),
        ],
    ),
    # « document divers » et « inconnu » n'ont pas d'indice : ce sont des états,
    # pas des catégories à deviner.
    Categorie(id="misc", label="Document divers", active=False),
    Categorie(id="unknown", label="Document inconnu", active=False),
]


class DocumentClassifier:
    """Classe un document à partir de son texte, avec preuves et révision."""

    def __init__(self, profiles_dir: Optional[Path] = None,
                 user_types_dir: Optional[Path] = None) -> None:
        self.categories: dict[str, Categorie] = {}
        for cat in _BUILTIN:
            self.categories[cat.id] = cat
        self._compile_cache: dict[str, list[tuple[re.Pattern, Indicateur]]] = {}

        if profiles_dir is not None:
            self._charge_depuis_profils(profiles_dir)
        if user_types_dir is not None:
            self._charge_types_utilisateur(user_types_dir)

    # ───────────────────────────── chargement ──────────────────────────────

    def _charge_depuis_profils(self, profiles_dir: Path) -> None:
        """Complète les catégories avec les motifs des profils d'extraction.

        Un profil déclare `document_types` : chaque type déclaré hérite des
        motifs des champs du profil. Un type inconnu crée une catégorie
        nouvelle, marquée `profile:<nom>`, sans écraser une catégorie intégrée.
        """
        if not profiles_dir.is_dir():
            return
        for chemin in sorted(profiles_dir.glob("*.json")):
            try:
                data = json.loads(chemin.read_text(encoding="utf-8"))
            except Exception as exc:
                log.warning("profil illisible pour la classification (%s) : %s",
                            chemin.name, exc)
                continue
            champs = data.get("fields") or []
            if not champs:
                continue
            for type_doc in data.get("document_types") or []:
                if type_doc in ("any", ""):
                    continue
                cat = self.categories.get(type_doc)
                if cat is None:
                    cat = Categorie(id=type_doc,
                                    label=data.get("label") or type_doc,
                                    source=f"profile:{data.get('name', chemin.stem)}",
                                    profil=data.get("name"))
                    self.categories[type_doc] = cat
                # les motifs de champs deviennent des indices complémentaires
                for ch in champs:
                    for motif in ch.get("patterns") or []:
                        cat.indicateurs.append(Indicateur(
                            motif=motif, poids=0.5,
                            libelle=f"champ {ch.get('key')}"))

    def _charge_types_utilisateur(self, dossier: Path) -> None:
        """Catégories ajoutées par l'utilisateur (JSON).

        Format : `{"id": "...", "label": "...", "indicators": [{"pattern":
        "...", "weight": 1.0, "label": "..."}]}`. Une catégorie sans indicateur
        est enregistrée mais désactivée — elle ne sera jamais proposée.
        """
        if not dossier.is_dir():
            return
        for chemin in sorted(dossier.glob("*.json")):
            try:
                data = json.loads(chemin.read_text(encoding="utf-8"))
            except Exception as exc:
                log.warning("type documentaire illisible (%s) : %s", chemin.name, exc)
                continue
            cid = str(data.get("id") or "").strip()
            if not cid:
                continue
            indicateurs = [
                Indicateur(motif=str(i.get("pattern")),
                           poids=float(i.get("weight", 1.0)),
                           libelle=str(i.get("label", "")))
                for i in (data.get("indicators") or []) if i.get("pattern")
            ]
            self.categories[cid] = Categorie(
                id=cid, label=str(data.get("label") or cid),
                indicateurs=indicateurs, source=f"user:{chemin.name}",
                active=bool(indicateurs), profil=data.get("profile"),
            )

    # ───────────────────────────── classification ──────────────────────────

    def _indicateurs_compiles(self, cat: Categorie) -> list[tuple[re.Pattern, Indicateur]]:
        if cat.id not in self._compile_cache:
            compiles = []
            for ind in cat.indicateurs:
                try:
                    compiles.append((ind.compile(), ind))
                except re.error as exc:
                    log.warning("indice ignoré (%s/%s) : %s", cat.id, ind.motif, exc)
            self._compile_cache[cat.id] = compiles
        return self._compile_cache[cat.id]

    def score_categorie(self, cat: Categorie, texte: str) -> tuple[float, list[dict]]:
        """Couverture des indices distinctifs + détail de toutes les preuves.

        La confiance est la part des indices **distinctifs** (poids >= 1)
        réellement matchés. Les indices hérités des profils (poids 0,5)
        apparaissent dans les preuves mais n'entrent pas au dénominateur : ils
        sont trop peu discriminants pour juger un document, trop utiles pour
        être cachés.
        """
        compiles = self._indicateurs_compiles(cat)
        if not compiles:
            return 0.0, []
        preuves: list[dict] = []
        obtenu_principal = 0.0
        obtenu_complementaire = 0.0
        for motif, ind in compiles:
            m = motif.search(texte)
            if m:
                if ind.poids >= 1.0:
                    obtenu_principal += ind.poids
                else:
                    obtenu_complementaire += ind.poids
                preuves.append({
                    "indicator": ind.libelle or ind.motif,
                    "pattern": ind.motif,
                    "weight": ind.poids,
                    "kind": "distinctive" if ind.poids >= 1.0 else "complementary",
                    "matched_text": m.group(0)[:60],
                })
        denom = cat.poids_principal()
        if denom <= 0:
            # catégorie sans indice distinctif : on retombe sur la couverture
            # de tous les indices plutôt que de diviser par zéro.
            denom = cat.poids_total()
        # confiance saturante sur le poids distinctif obtenu
        confiance = obtenu_principal / (obtenu_principal + ABSORPTION)
        return min(confiance, CONFIANCE_MAX), preuves

    def classify(self, texte: str) -> ClassificationResult:
        """Classe un texte. Ne force jamais une catégorie sous le seuil."""
        texte = texte or ""
        resultats: list[tuple[float, Categorie, list[dict]]] = []
        for cat in self.categories.values():
            if not cat.active or not cat.indicateurs:
                continue
            score, preuves = self.score_categorie(cat, texte)
            if score > 0:
                resultats.append((score, cat, preuves))
        resultats.sort(key=lambda t: t[0], reverse=True)

        if not resultats:
            return ClassificationResult(
                category="unknown", label=self.categories["unknown"].label,
                confidence=0.0,
                reason="aucun indice reconnu : le document part en révision",
                needs_review=True,
            )

        meilleur, cat, preuves = resultats[0]
        # plafond : un classifieur n'est jamais certain à 100 %
        confiance = min(meilleur, 0.95)
        alternatives = [
            {"category": c.id, "label": c.label, "confidence": round(s, 3)}
            for s, c, _ in resultats[1:4]
        ]

        motifs = []
        if confiance < SEUIL_ACCEPTATION:
            motifs.append(f"confiance {confiance:.2f} < seuil {SEUIL_ACCEPTATION}")
        if len(resultats) > 1 and (meilleur - resultats[1][0]) < MARGE_AMBIGUITE:
            motifs.append(
                f"ambiguïté avec « {resultats[1][1].label} » "
                f"(écart {meilleur - resultats[1][0]:.2f} < {MARGE_AMBIGUITE})"
            )

        if confiance < SEUIL_REVISION:
            return ClassificationResult(
                category="unknown", label=self.categories["unknown"].label,
                confidence=confiance, evidence=preuves, alternatives=alternatives,
                reason="; ".join(motifs) or "confiance insuffisante",
                needs_review=True,
            )

        return ClassificationResult(
            category=cat.id, label=cat.label, confidence=confiance,
            evidence=preuves, alternatives=alternatives,
            needs_review=bool(motifs), reason="; ".join(motifs),
        )

    def profil_pour(self, category: str) -> Optional[str]:
        cat = self.categories.get(category)
        return cat.profil if cat else None

    def disabled_categories(self) -> list[dict[str, str]]:
        """Catégories déclarées mais sans indice — à rendre visible, pas à cacher."""
        return [{"id": c.id, "label": c.label, "source": c.source}
                for c in self.categories.values() if not c.active]


def classification_manuelle(category: str, user: str,
                            categories: Optional[Iterable[str]] = None) -> ClassificationResult:
    """Pose une catégorie à la main (document inconnu classé par un humain)."""
    connues = set(categories) if categories else set(_BUILTIN_LABELS)
    if category not in connues:
        raise ValueError(f"catégorie inconnue : {category}")
    return ClassificationResult(
        category=category, label=_BUILTIN_LABELS.get(category, category),
        confidence=1.0, classifier_version=CLASSIFIER_VERSION,
        needs_review=False, reason="classification manuelle",
        manual=True, corrected_by=user,
    )


_BUILTIN_LABELS: dict[str, str] = {c.id: c.label for c in _BUILTIN}


def consigne_classification(log_dir: Path, job_id: str, resultat: ClassificationResult,
                            manuel: bool = False) -> None:
    """Trace la classification dans le journal d'audit."""
    audit(log_dir, "document_classified", job_id=job_id,
          category=resultat.category, confidence=round(resultat.confidence, 3),
          classifier_version=resultat.classifier_version,
          needs_review=resultat.needs_review, manual=manuel or resultat.manual,
          evidence_count=len(resultat.evidence))
