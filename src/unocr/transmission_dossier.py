"""Transmission d'un dossier entier vers un connecteur (étape 14).

**Ce que ce module fait.** Un dossier, une fois son paquet de données généré
(étape 13), doit pouvoir partir vers un connecteur opérationnel — comme un
document isolé le fait déjà via `POST /api/connectors/transmit`. Jusqu'ici la
transmission ne portait que sur un `job_id` : un dossier entier ne pouvait pas
partir, il fallait transmettre ses documents un par un et perdre la structure.

**Ce qu'il transmet.** Les valeurs du formulaire du dossier (étape 12),
**mappées** vers le formulaire cible du connecteur. **Jamais les fichiers**
eux-mêmes : un dossier transmet ses données, pas ses pièces jointes. C'est un
choix, pas une limite technique — embarquer les originaux dans un envoi
sortant est une décision qui appartient à l'utilisateur.

**Pourquoi un mapping et pas un envoi direct des clés du dossier.** Les clés
d'un formulaire de dossier (`invoice_number`, `gross_weight`) ne sont pas les
clés du système cible (`containerNo`, `bl_reference`). Les envoyer telles
quelles produirait un rejet, ou pire, un enregistrement silencieusement faux.
Le dossier passe donc par le même `MappingEngine` qu'un document : sans
formulaire cible ni règle de correspondance, la transmission est **refusée** —
on ne devine jamais une structure.

**La règle absolue, héritée du Connecteur Hub.** `SENT` n'est pas `ACCEPTED`.
Tant qu'aucune preuve d'acceptation n'est revenue, le système ne suppose
jamais que le dossier a été enregistré chez le cible. L'état affiché reflète
la preuve obtenue, pas l'intention. Et deux envois du même contenu vers le
même connecteur produisent la même clé d'idempotence : le second n'est pas
renvoyé.

**Le verrou.** Aucune transmission de dossier n'est possible sans un rapport
de contrôle passé en paramètre : pièces requises manquantes, champs non
validés par un humain, anomalies de cohérence non tranchées. Le refus est
posé ici, pas dans l'interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .connectors.contract import OPERATIONAL_STATES, FormSchema
from .connectors.mapping import MappedValue, MappingRule, apply_transform
from .connectors.transmission import TransmissionEngine, TransmissionStatus
from .connectors.validation import (
    RiskLevel,
    ValidationIssue,
    ValidationReport,
)
from .dossier import DossierStore
from .formulaire import ChampFormulaire, FormulaireDossier
from .logging_setup import get_logger

log = get_logger("transmission_dossier")

#: ce que la transmission d'un dossier NE garantit PAS. Affiché à côté de
#: tout envoi, et renvoyé par chaque réponse d'API de transmission.
CE_QUE_LA_TRANSMISSION_NE_GARANTIT_PAS = [
    "L'envoi ne prouve pas que le dossier a été accepté : « envoyé » n'est "
    "pas « accepté ».",
    "Aucun accusé de réception n'est supposé tant qu'aucune preuve n'est "
    "revenue du système cible.",
    "La transmission ne rend rien inaltérable : ce qui part reste une copie "
    "modifiable chez le destinataire.",
    "Un échec technique laisse l'issue inconnue — le dossier est à "
    "rapprocher, jamais supposé enregistré.",
    "Les documents originaux ne sont pas joints : seules les valeurs du "
    "formulaire sont transmises.",
]


@dataclass
class ApercuTransmissionDossier:
    """Ce qui part, ce qui manque, ce qui est douteux.

    Volontairement sans méthode `envoyer()` : un aperçu ne transmet rien,
    quelle que soit la pression de l'appelant.
    """
    dossier_id: str
    label: str
    #: valeurs réellement candidates à l'envoi, indexées par champ **cible**
    valeurs: dict[str, MappedValue] = field(default_factory=dict)
    issues: list[ValidationIssue] = field(default_factory=list)
    #: contenu tel qu'il partirait — les données, pas les fichiers
    contenu: dict[str, Any] = field(default_factory=dict)
    #: formulaire cible retenu, ou None si aucun n'a pu être résolu
    form_id: str = ""
    pieces: int = 0

    @property
    def erreurs(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def avertissements(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def transmissible(self) -> bool:
        return not self.erreurs

    def as_dict(self) -> dict[str, Any]:
        return {
            "dossier_id": self.dossier_id,
            "label": self.label,
            "pieces": self.pieces,
            "form_id": self.form_id,
            "valeurs": {k: v.as_dict() for k, v in self.valeurs.items()},
            "issues": [i.as_dict() for i in self.issues],
            "contenu": self.contenu,
            "transmissible": self.transmissible,
            "ne_garantit_pas": list(CE_QUE_LA_TRANSMISSION_NE_GARANTIT_PAS),
        }


def _mappe(champs: list[ChampFormulaire], rules: list[MappingRule],
           form_cible: Optional[FormSchema]) -> dict[str, MappedValue]:
    """Applique les règles de correspondance dossier → cible.

    **Pourquoi pas `MappingEngine.apply()`.** Le moteur existant produit une
    confiance `explicit` ou `exact` selon l'origine de la règle, et perd
    l'information « validée par un humain ». Or c'est précisément cette
    information qui doit faire bloquer le `Validator` : une valeur sortie de
    l'OCR et non relue ne doit pas partir vers un système réel comme si elle
    était confirmée. Le mapping est donc refait ici, en conservant la
    confiance, et en réutilisant `apply_transform` pour rester cohérent avec
    les transformations du hub.
    """
    par_source = {r.source_field: r for r in rules}
    noms_cible = set()
    if form_cible is not None:
        noms_cible = {getattr(f, "external_name", "") or ""
                      for f in form_cible.fields}

    out: dict[str, MappedValue] = {}
    for c in champs:
        if not c.est_rempli:
            continue
        rule = par_source.get(c.key)
        cible = rule.target_field if rule is not None else c.key
        if noms_cible and cible not in noms_cible:
            continue                       # champ inconnu du système cible
        brute = None if c.valeur is None else str(c.valeur)
        valeur, avertissement = brute, ""
        if rule is not None and rule.transform:
            valeur, avertissement = apply_transform(brute, rule.transform)
        out[cible] = MappedValue(
            target_field=cible, value=valeur,
            confidence="explicit" if c.valide else "suggested",
            source_field=c.key,
            transform=rule.transform if rule is not None else "",
            ocr_raw=brute, warning=avertissement,
        )
    return out


def _source_depuis_formulaire(
        formulaire: FormulaireDossier) -> dict[str, MappedValue]:
    """Les champs du dossier, tels qu'ils sont — pour l'affichage de l'aperçu.

    La confiance distingue une valeur **validée par un humain** d'une valeur
    qui vient de l'extraction.
    """
    source: dict[str, MappedValue] = {}
    for c in formulaire.champs:
        if not c.est_rempli:
            continue
        source[c.key] = MappedValue(
            target_field=c.key,
            value=None if c.valeur is None else str(c.valeur),
            confidence="explicit" if c.valide else "suggested",
            source_field=c.key,
            ocr_raw=None if c.valeur is None else str(c.valeur),
        )
    return source


def apercu_transmission_dossier(dossier, synthese: dict,
                                formulaire: Optional[FormulaireDossier],
                                form_cible: Optional[FormSchema] = None,
                                rules: Iterable[MappingRule] = (),
                                anomalies: Iterable[dict] = (),
                                ) -> ApercuTransmissionDossier:
    """Construit l'aperçu de ce qui serait transmis. N'envoie rien.

    Règles de contrôle, dans l'ordre :
    - **aucun formulaire cible** bloque : on ne devine jamais une structure ;
    - une pièce **requise** manquante bloque : transmettre un dossier
      incomplet comme s'il était complet est le pire des silences ;
    - un champ du dossier **non couvert par une règle de mapping** bloque :
      il serait perdu sans que personne le sache ;
    - un champ rempli mais **non validé par un humain** avertit : la valeur
      vient de l'OCR, elle peut être fausse ;
    - une anomalie de cohérence **non tranchée** avertit.
    """
    ap = ApercuTransmissionDossier(
        dossier_id=dossier.id, label=dossier.label,
        pieces=len(dossier.pieces or []),
        form_id=form_cible.form_id if form_cible else "",
    )

    # 1. sans formulaire cible, rien ne part
    if form_cible is None:
        ap.issues.append(ValidationIssue(
            field="", kind="missing_required", severity="error",
            message=("aucun formulaire cible : indiquez le formulaire du "
                     "connecteur et les règles de correspondance. On ne "
                     "devine jamais la structure attendue par le système "
                     "cible."),
        ))

    # 2. pièces requises manquantes — le dossier est incomplet
    for manquante in synthese.get("requises_manquantes") or []:
        ap.issues.append(ValidationIssue(
            field=manquante.get("category", ""),
            kind="missing_required",
            severity="error",
            message=(f"pièce requise absente : {manquante.get('label', '')} — "
                     "l'envoi laisserait croire que le dossier est complet"),
        ))

    champs = list(formulaire.champs) if formulaire else []
    if not champs:
        ap.issues.append(ValidationIssue(
            field="", kind="missing_required", severity="error",
            message=("aucun champ à transmettre : aucun document de ce dossier "
                     "n'a fourni de valeur extractible"),
        ))
        ap.contenu = _contenu(dossier, ap, {})
        return ap

    mappe = _mappe(champs, list(rules), form_cible)

    # 4. un champ du dossier sans règle de correspondance serait perdu
    couverts = {r.source_field for r in rules}
    for c in champs:
        if not c.est_rempli:
            if c.required:
                ap.issues.append(ValidationIssue(
                    field=c.key, kind="missing_required", severity="error",
                    message=f"champ requis non rempli : {c.label or c.key}",
                ))
            continue
        if c.key not in couverts:
            ap.issues.append(ValidationIssue(
                field=c.key, kind="unknown_field", severity="error",
                message=(f"« {c.label or c.key} » n'a pas de correspondance "
                         "vers le formulaire cible : il serait perdu à "
                         "l'envoi"),
            ))
        if not c.valide:
            ap.issues.append(ValidationIssue(
                field=c.key, kind="unvalidated_suggestion", severity="warning",
                message=(f"« {c.label or c.key} » vient de l'extraction et "
                         "n'a pas été validée par un humain"),
            ))

    ap.valeurs = mappe
    ap.contenu = _contenu(dossier, ap, {
        k: v.value for k, v in mappe.items()
        if v.value is not None and v.confidence != "suggested"})

    # 5. anomalies de cohérence non tranchées
    for a in anomalies:
        if a.get("statut") in ("", "a_trancher", None):
            ap.issues.append(ValidationIssue(
                field=str(a.get("champ") or a.get("regle") or ""),
                kind="contradiction", severity="warning",
                message=(f"anomalie non tranchée : {a.get('message', '')} — "
                         "deux documents du dossier se contredisent"),
            ))
    return ap


def _contenu(dossier, ap: ApercuTransmissionDossier,
             valeurs: dict) -> dict[str, Any]:
    """Le contenu tel qu'il partirait — **pas** ce qui a été saisi.

    Une valeur non validée par un humain est exclue, exactement comme le fait
    `ValidationReport.payload()` : afficher dans l'aperçu une valeur qui ne
    partira pas serait un aperçu mensonger.
    """
    return {
        "dossier": {
            "label": dossier.label,
            "profile": getattr(dossier, "profile", ""),
            "pieces": ap.pieces,
        },
        "champs": valeurs,
        # rappel dans le contenu lui-même : ce qui n'est PAS joint
        "fichiers_joints": False,
    }


def rapport_depuis_apercu(ap: ApercuTransmissionDossier, risk: RiskLevel,
                          confirmed: bool = False,
                          confirmed_by: str = "") -> ValidationReport:
    """Transforme un aperçu en rapport de validation transmissible.

    Le rapport reste celui de `connectors.validation` : le verrou posé par
    `TransmissionEngine.create()` s'applique donc à l'identique.
    """
    report = ValidationReport(form_id=ap.form_id or f"dossier:{ap.dossier_id}",
                              risk=risk, issues=list(ap.issues),
                              values=dict(ap.valeurs))
    if confirmed:
        report.confirm(by=confirmed_by or "utilisateur")
    return report


def _formulaire_depuis_dossier(dossier, formulaires) -> Optional[FormulaireDossier]:
    """Dernier formulaire enregistré d'un dossier, ou une construction à la volée."""
    existants = [f for f in formulaires.liste() if f.dossier_id == dossier.id]
    return existants[-1] if existants else None


def resout_form_cible(hub, form_store, form_id: str) -> Optional[FormSchema]:
    """Trouve le formulaire cible : id explicite, sinon celui du connecteur
    opérationnel. Renvoie None si aucun schéma n'est disponible — on ne
    devine jamais une structure.
    """
    if form_id:
        local = form_store.get(form_id)
        if local is not None and getattr(local, "active", True):
            return local.schema()
        for cid in [r["connector_id"] for r in hub.list_configured()]:
            inst = hub.get(cid)
            if inst is None:
                continue
            try:
                for f in inst.discover_forms():
                    if f.form_id == form_id:
                        return f
            except Exception:
                continue
        return None
    for cid in [r["connector_id"] for r in hub.list_configured()]:
        inst = hub.get(cid)
        if inst is None or inst.state not in OPERATIONAL_STATES:
            continue
        try:
            forms = inst.discover_forms()
            if forms:
                return forms[0]
        except Exception:
            continue
    return None


def transmettre_dossier(dossiers: DossierStore, transmissions: TransmissionEngine,
                        hub, dossier_id: str, documents_dossier,
                        formulaires, form_store, form_id: str = "",
                        rules: Iterable[MappingRule] = (),
                        risque: str = "medium", confirme: bool = False,
                        confirme_par: str = "", anomalies: Iterable[dict] = (),
                        ) -> dict:
    """Transmet le contenu d'un dossier vers un connecteur opérationnel.

    Lève `KeyError` si le dossier n'existe pas, `ValueError` si la
    transmission est refusée (rapport non transmissible, aucun formulaire
    cible, aucun connecteur opérationnel). Ce sont des refus, jamais des
    demi-envois.
    """
    dossier = dossiers.get(dossier_id)
    if dossier is None:
        raise KeyError(f"dossier introuvable : {dossier_id}")

    synthese = dossiers.synthese(dossier)
    formulaire = _formulaire_depuis_dossier(dossier, formulaires)
    if formulaire is None:
        from .formulaire import construit_depuis_dossier
        formulaire = construit_depuis_dossier(dossier, documents_dossier(dossier))

    form_cible = resout_form_cible(hub, form_store, form_id)
    ap = apercu_transmission_dossier(dossier, synthese, formulaire, form_cible,
                                     list(rules), anomalies)
    try:
        risk = RiskLevel(risque)
    except ValueError:
        risk = RiskLevel.MEDIUM
    report = rapport_depuis_apercu(ap, risk, confirme, confirme_par)

    # le connecteur doit être opérationnel (test réel réussi)
    cible = None
    for cid in [r["connector_id"] for r in hub.list_configured()]:
        inst = hub.get(cid)
        if inst is not None and inst.state in OPERATIONAL_STATES:
            cible = inst
            break
    if cible is None:
        raise ValueError("aucun connecteur opérationnel : configurez puis "
                         "testez-en un avant de transmettre")

    form = form_cible or FormSchema(form_id=report.form_id,
                                    label=f"Dossier — {dossier.label}",
                                    organization=cible.organization,
                                    source="declared")

    try:
        tx = transmissions.create(cible.connector_id, form, report,
                                  dossier_id=dossier_id)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    deja = (tx.status in (TransmissionStatus.ACCEPTED, TransmissionStatus.SENT,
                          TransmissionStatus.PENDING_CONFIRMATION)
            and not tx.needs_send)
    if not deja:
        tx = transmissions.send(tx.transmission_id, cible)

    # tracé dans le journal du dossier — la transmission fait partie de son
    # histoire, au même titre que l'archivage
    dossiers.journaliser(dossier_id, "transmitted", {
        "transmission": tx.transmission_id,
        "connector": cible.connector_id,
        "formulaire": form.form_id,
        "statut": tx.status.value,
        "champs": len(tx.payload),
        "confirme_par": tx.confirmed_by,
        "ne_garantit_pas": CE_QUE_LA_TRANSMISSION_NE_GARANTIT_PAS[0],
    }, acteur=confirme_par or "utilisateur")

    return {
        "dossier_id": dossier_id,
        "apercu": ap.as_dict(),
        "transmission": tx.as_dict(),
        "connector_id": cible.connector_id,
        "is_real_external_system": cible.is_real_external_system,
        "renvoye_evite": deja,
        "ne_garantit_pas": list(CE_QUE_LA_TRANSMISSION_NE_GARANTIT_PAS),
    }
