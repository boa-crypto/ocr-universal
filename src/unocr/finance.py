"""Rapprochement bancaire et agrégats financiers multi-devises.

Les opérations bancaires sont importées explicitement (JSON ou CSV), jamais
inventées. Elles sont dédupliquées par identifiant externe ou par empreinte
stable. Le rapprochement automatique ne lie une facture que si une seule
opération est candidate et qu'un indice au moins corrobore le montant ;
sinon il signale l'ambiguïté. Les totaux financiers sont agrégés par devise :
aucune conversion implicite n'est appliquée.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import time
import unicodedata
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .business_store import BusinessStore
from .logging_setup import audit
from .models import Facture, Frais

CENTIME = Decimal("0.01")
MAX_OPERATIONS_IMPORT = 10_000

#: Champs qu'un pointage bancaire rend cohérents avec l'opération liée.
#: Les notes et documents restent modifiables ; ces champs exigent d'abord
#: l'annulation explicite du rapprochement.
CHAMPS_FACTURE_POINTES = frozenset({
    "dossier_id", "type_facture", "numero_facture", "date_facture",
    "montant_ht", "montant_tva", "montant_ttc", "devise",
    "statut_paiement", "date_paiement", "reference_paiement", "mode_paiement",
})


class OperationBancaire(BaseModel):
    id: str
    dossier_id: str
    date: str
    montant: float
    devise: str = "EUR"
    reference: str = ""
    libelle: str = ""
    contrepartie: str = ""
    identifiant_externe: str = ""
    empreinte: str = ""
    statut: str = "non_rapprochee"  # non_rapprochee, rapprochee
    facture_id: Optional[str] = None
    importe_par: str = ""
    created_at: float = Field(default_factory=time.time)
    #: État de paiement de la facture avant pointage, restauré à l'annulation.
    paiement_facture_avant: Optional[dict[str, Any]] = None


def store_operations(cfg: Any) -> BusinessStore[OperationBancaire]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "operation_bancaire", OperationBancaire)


def _decimal(valeur: Any) -> Decimal:
    """Lit un montant fini, sans arrondir silencieusement un tiers de centime.

    Formats acceptés : ``1234.56``, ``1234,56``, ``1 234,56``, ``1,234.56``,
    ``1.234,56`` et parenthèses négatives. ``1,234`` seul est refusé : il peut
    signifier 1234 ou 1.234 selon la banque.
    """
    if valeur is None or isinstance(valeur, bool):
        raise HTTPException(422, f"Montant invalide : {valeur!r}")
    texte = re.sub(r"[\s\u00a0\u202f\u2009]+", "", str(valeur))
    if texte.startswith("(") and texte.endswith(")"):
        texte = "-" + texte[1:-1]
    try:
        if "," in texte and "." in texte:
            separateur = "," if texte.rfind(",") > texte.rfind(".") else "."
            milliers = "." if separateur == "," else ","
            entier, _, decimales = texte.rpartition(separateur)
            if not 1 <= len(decimales) <= 2 or not decimales.isdigit():
                raise ValueError("décimales invalides")
            if not re.fullmatch(r"[+-]?\d{1,3}(?:" + re.escape(milliers) + r"\d{3})+", entier):
                raise ValueError("séparateur de milliers invalide")
            texte = entier.replace(milliers, "") + "." + decimales
        elif "," in texte:
            if texte.count(",") != 1:
                raise ValueError("séparateur décimal ambigu")
            texte = texte.replace(",", ".")
        if texte.count(".") > 1 or not re.fullmatch(r"[+-]?\d+(?:\.\d{1,2})?", texte):
            raise ValueError("montant ambigu ou précision supérieure au centime")
        montant = Decimal(texte)
        if not montant.is_finite():
            raise ValueError("montant non fini")
        return montant.quantize(CENTIME, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(422, f"Montant invalide : {valeur!r}") from exc


def _arrondi(valeur: Decimal) -> float:
    return float(valeur.quantize(CENTIME, rounding=ROUND_HALF_UP))


def _date_iso(valeur: str, champ: str) -> str:
    try:
        return date.fromisoformat(valeur).isoformat()
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, f"{champ} : date ISO attendue (AAAA-MM-JJ)") from exc


def _devise(valeur: str) -> str:
    code = (valeur or "EUR").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise HTTPException(422, "Devise invalide : code ISO à 3 lettres attendu")
    return code


def _empreinte(dossier_id: str, identifiant_externe: str, date_op: str, montant: Decimal,
               devise: str, reference: str, libelle: str, contrepartie: str = "") -> str:
    if identifiant_externe:
        base = {"dossier": dossier_id, "id_externe": identifiant_externe}
    else:
        base = {"dossier": dossier_id, "date": date_op, "montant": str(montant),
                "devise": devise, "reference": reference, "libelle": libelle,
                "contrepartie": contrepartie}
    canon = json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _meme_contenu(operation: OperationBancaire, date_op: str, montant: Decimal,
                  devise: str, reference: str, libelle: str, contrepartie: str) -> bool:
    return (operation.date == date_op and _decimal(operation.montant) == montant
            and operation.devise == devise and operation.reference == reference
            and operation.libelle == libelle and operation.contrepartie == contrepartie)


def importer_operations(cfg: Any, dossier_id: str, lignes: list[dict[str, Any]],
                        acteur: str) -> dict[str, Any]:
    """Importe et déduplique des opérations bancaires pour un dossier.

    Un identifiant externe déjà connu avec un contenu différent est un rejet,
    pas un doublon silencieux : l'opérateur doit corriger le relevé ou fournir
    un nouvel identifiant banque.
    """
    if len(lignes) > MAX_OPERATIONS_IMPORT:
        raise HTTPException(413, f"Import limité à {MAX_OPERATIONS_IMPORT} opérations")
    importees: list[str] = []
    doublons = 0
    rejetees: list[dict[str, Any]] = []
    with store_operations(cfg).transaction() as transaction:
        for index, ligne in enumerate(lignes):
            try:
                if not isinstance(ligne, dict):
                    raise HTTPException(422, "Objet d'opération attendu")
                date_op = _date_iso(str(ligne.get("date", "")), "Date d'opération")
                montant = _decimal(ligne.get("montant"))
                devise = _devise(str(ligne.get("devise", "EUR")))
                reference = str(ligne.get("reference", "") or "").strip()
                libelle = str(ligne.get("libelle", "") or "").strip()
                contrepartie = str(ligne.get("contrepartie", "") or "").strip()
                identifiant_externe = str(ligne.get("identifiant_externe")
                                          or ligne.get("id_externe") or "").strip()
                empreinte = _empreinte(dossier_id, identifiant_externe, date_op, montant,
                                       devise, reference, libelle, contrepartie)
                identifiant = "op_" + empreinte[:24]
                existante = transaction.get(identifiant)
                if existante is not None:
                    if identifiant_externe and not _meme_contenu(
                            existante, date_op, montant, devise, reference, libelle, contrepartie):
                        raise HTTPException(
                            409, "Identifiant externe déjà importé avec un contenu différent")
                    doublons += 1
                    continue
                operation = OperationBancaire(
                    id=identifiant, dossier_id=dossier_id, date=date_op,
                    montant=_arrondi(montant), devise=devise, reference=reference,
                    libelle=libelle, contrepartie=contrepartie,
                    identifiant_externe=identifiant_externe, empreinte=empreinte,
                    importe_par=acteur,
                )
                transaction[identifiant] = operation
                importees.append(identifiant)
            except HTTPException as exc:
                rejetees.append({"ligne": index, "erreur": str(exc.detail),
                                 "statut": exc.status_code})
    audit(cfg.log_dir, "banque_import", dossier=dossier_id, acteur=acteur,
          importees=len(importees), doublons=doublons, rejetees=len(rejetees))
    return {"importees": len(importees), "doublons": doublons, "rejetees": rejetees,
            "operations": importees}


def _normaliser_entete(entete: str) -> str:
    texte = unicodedata.normalize("NFKD", entete or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", texte.lower()).strip("_")


ALIASES_CSV = {
    "date": "date", "date_operation": "date", "date_valeur": "date",
    "montant": "montant", "amount": "montant",
    "devise": "devise", "currency": "devise",
    "reference": "reference", "ref": "reference", "reference_paiement": "reference",
    "libelle": "libelle", "label": "libelle", "description": "libelle",
    "contrepartie": "contrepartie", "tiers": "contrepartie", "beneficiaire": "contrepartie",
    "identifiant_externe": "identifiant_externe", "id_externe": "identifiant_externe",
    "id_banque": "identifiant_externe", "transaction_id": "identifiant_externe",
}


def parser_csv_banque(contenu: str) -> list[dict[str, Any]]:
    """Lit un CSV bancaire simple (`,` ou `;`), sans pré-normaliser les montants."""
    if not contenu.strip():
        raise HTTPException(422, "CSV bancaire vide")
    premiere = contenu.splitlines()[0]
    delimiteur = ";" if premiere.count(";") >= premiere.count(",") else ","
    lecteur = csv.DictReader(io.StringIO(contenu), delimiter=delimiteur)
    if not lecteur.fieldnames:
        raise HTTPException(422, "CSV bancaire sans en-tête")
    colonnes: dict[str, str] = {}
    champs_vus: set[str] = set()
    for original in lecteur.fieldnames:
        normal = _normaliser_entete(original)
        champ = ALIASES_CSV.get(normal)
        if not champ:
            continue
        if champ in champs_vus:
            raise HTTPException(422, f"CSV bancaire : colonne dupliquée pour {champ}")
        champs_vus.add(champ)
        colonnes[champ] = original
    if not {"date", "montant"} <= champs_vus:
        raise HTTPException(422, "CSV bancaire : colonnes date et montant requises")
    lignes: list[dict[str, Any]] = []
    for numero, brut in enumerate(lecteur, start=2):
        if None in brut:
            raise HTTPException(422, f"CSV bancaire : ligne {numero} avec colonnes surnuméraires")
        ligne = {champ: (brut.get(original) or "").strip()
                 for champ, original in colonnes.items()}
        if not any(ligne.values()):
            continue
        lignes.append(ligne)
        if len(lignes) > MAX_OPERATIONS_IMPORT:
            raise HTTPException(413, f"Import limité à {MAX_OPERATIONS_IMPORT} opérations")
    return lignes


def _montant_facture(facture: Facture) -> Decimal:
    """TTC renseigné, sinon HT + TVA ; refuse un montant non exploitable."""
    ttc = _decimal(facture.montant_ttc)
    if ttc:
        return ttc
    ht = _decimal(facture.montant_ht)
    tva = _decimal(facture.montant_tva)
    total = (ht + tva).quantize(CENTIME, rounding=ROUND_HALF_UP)
    if not total:
        raise HTTPException(422, "Facture sans montant exploitable")
    return total


def _sens_attendu(facture: Facture) -> Optional[int]:
    if facture.type_facture == "emisee":
        return 1
    if facture.type_facture == "recue":
        return -1
    return None


def _compatible(facture: Facture, operation: OperationBancaire) -> bool:
    if facture.devise.strip().upper() != operation.devise.strip().upper():
        return False
    montant_op = _decimal(operation.montant)
    sens = _sens_attendu(facture)
    if sens is not None and montant_op * sens <= 0:
        return False
    return abs(montant_op) == abs(_montant_facture(facture))


def _score(facture: Facture, operation: OperationBancaire) -> int:
    score = 1  # montant + devise compatibles
    reference = (facture.numero_facture or "").strip().lower()
    texte = " ".join([operation.reference, operation.libelle, operation.contrepartie]).lower()
    if reference and re.search(r"(?<![a-z0-9])" + re.escape(reference) + r"(?![a-z0-9])", texte):
        score += 2
    if facture.date_facture and operation.date:
        try:
            ecart = abs((date.fromisoformat(facture.date_facture)
                         - date.fromisoformat(operation.date)).days)
            if ecart <= 3:
                score += 1
        except ValueError:
            pass
    return score


def _lier(transaction: BusinessStore, facture: Facture, operation: OperationBancaire) -> None:
    if facture.rapprochee or facture.operation_bancaire_id:
        raise HTTPException(409, "Facture déjà rapprochée")
    if operation.statut == "rapprochee" or operation.facture_id:
        raise HTTPException(409, "Opération bancaire déjà rapprochée")
    operation.paiement_facture_avant = {
        "statut_paiement": facture.statut_paiement,
        "date_paiement": facture.date_paiement,
        "reference_paiement": facture.reference_paiement,
    }
    factures = transaction.related("facture", Facture)
    facture.rapprochee = True
    facture.operation_bancaire_id = operation.id
    facture.statut_paiement = "payee"
    facture.date_paiement = operation.date
    facture.reference_paiement = operation.reference
    factures[facture.id] = facture
    operation.statut = "rapprochee"
    operation.facture_id = facture.id
    transaction[operation.id] = operation


def verifier_modification_facture(avant: Facture, apres: Facture) -> None:
    if not (avant.rapprochee or avant.operation_bancaire_id):
        return
    changes = sorted(champ for champ in CHAMPS_FACTURE_POINTES
                     if getattr(avant, champ) != getattr(apres, champ))
    if changes:
        raise HTTPException(
            409, "Annulez le rapprochement avant de modifier : " + ", ".join(changes))


def rapprochement_auto(cfg: Any, dossier_id: str, date_debut: str, date_fin: str,
                       acteur: str) -> dict[str, Any]:
    debut = _date_iso(date_debut, "Date de début")
    fin = _date_iso(date_fin, "Date de fin")
    if debut > fin:
        raise HTTPException(422, "La date de début doit précéder la date de fin")
    operations_store = store_operations(cfg)
    rapprochees: list[dict[str, Any]] = []
    non_rapprochees: list[dict[str, Any]] = []
    with operations_store.transaction() as transaction:
        factures_store = transaction.related("facture", Facture)
        toutes = [f for f in factures_store.values() if f.dossier_id == dossier_id]
        factures = [f for f in toutes if not f.rapprochee and not f.operation_bancaire_id]
        operations = [op for op in transaction.values()
                      if op.dossier_id == dossier_id and op.statut != "rapprochee"
                      and not op.facture_id and debut <= op.date <= fin]
        for facture in factures:
            try:
                candidates = [op for op in operations if op.statut != "rapprochee"
                              and not op.facture_id and _compatible(facture, op)]
            except HTTPException as exc:
                non_rapprochees.append({"facture_id": facture.id,
                                        "raison": "facture_invalide", "erreur": str(exc.detail)})
                continue
            if not candidates:
                non_rapprochees.append({"facture_id": facture.id, "raison": "aucune_correspondance"})
                continue
            meilleur = max(_score(facture, op) for op in candidates)
            finalists = [op for op in candidates if _score(facture, op) == meilleur]
            if meilleur < 2:
                non_rapprochees.append({"facture_id": facture.id,
                                        "candidats": [op.id for op in finalists],
                                        "raison": "indice_insuffisant"})
                continue
            if len(finalists) > 1:
                non_rapprochees.append({"facture_id": facture.id,
                                        "candidats": [op.id for op in finalists],
                                        "raison": "multiples_correspondances"})
                continue
            operation = finalists[0]
            _lier(transaction, facture, operation)
            rapprochees.append({"facture_id": facture.id, "operation_id": operation.id,
                                "type": "automatique", "score": meilleur})
    for lien in rapprochees:
        audit(cfg.log_dir, "rapprochement_bancaire", dossier=dossier_id, acteur=acteur, **lien)
    deja = len(toutes) - len(factures)
    return {"rapprochees": rapprochees, "non_rapprochees": non_rapprochees,
            "total_factures": len(toutes), "deja_rapprochees": deja,
            "factures_a_rapprocher": len(factures),
            "operations_disponibles": len(operations),
            "taux_rapprochement": (deja + len(rapprochees)) / len(toutes) if toutes else 0}


def rapprochement_manuel(cfg: Any, dossier_id: str, facture_id: str, operation_id: str,
                         acteur: str, motif: str = "") -> dict[str, Any]:
    with store_operations(cfg).transaction() as transaction:
        factures_store = transaction.related("facture", Facture)
        facture = factures_store.get(facture_id)
        operation = transaction.get(operation_id)
        if facture is None or facture.dossier_id != dossier_id:
            raise HTTPException(404, "Facture introuvable pour ce dossier")
        if operation is None or operation.dossier_id != dossier_id:
            raise HTTPException(404, "Opération bancaire introuvable pour ce dossier")
        if facture.rapprochee or facture.operation_bancaire_id:
            raise HTTPException(409, "Facture déjà rapprochée")
        if operation.statut == "rapprochee" or operation.facture_id:
            raise HTTPException(409, "Opération bancaire déjà rapprochée")
        if not _compatible(facture, operation):
            raise HTTPException(422, "Montant ou devise incompatible avec la facture")
        _lier(transaction, facture, operation)
    audit(cfg.log_dir, "rapprochement_bancaire", dossier=dossier_id, acteur=acteur,
          facture=facture_id, operation=operation_id, type="manuel", motif=motif)
    return {"ok": True, "facture_id": facture_id, "operation_id": operation_id}


def annuler_rapprochement(cfg: Any, dossier_id: str, facture_id: str,
                          acteur: str, motif: str = "") -> dict[str, Any]:
    with store_operations(cfg).transaction() as transaction:
        factures_store = transaction.related("facture", Facture)
        facture = factures_store.get(facture_id)
        if facture is None or facture.dossier_id != dossier_id:
            raise HTTPException(404, "Facture introuvable pour ce dossier")
        if not facture.rapprochee and not facture.operation_bancaire_id:
            raise HTTPException(409, "Facture non rapprochée")
        operation_id = facture.operation_bancaire_id
        operation = transaction.get(operation_id) if operation_id else None
        if operation is not None and operation.facture_id not in (None, facture.id):
            raise HTTPException(409, "Opération bancaire liée à une autre facture")
        avant = operation.paiement_facture_avant if operation else None
        facture.rapprochee = False
        facture.operation_bancaire_id = None
        facture.statut_paiement = (avant or {}).get("statut_paiement") or "en_attente"
        facture.date_paiement = (avant or {}).get("date_paiement")
        facture.reference_paiement = (avant or {}).get("reference_paiement") or ""
        factures_store[facture.id] = facture
        if operation is not None:
            operation.statut = "non_rapprochee"
            operation.facture_id = None
            operation.paiement_facture_avant = None
            transaction[operation.id] = operation
    audit(cfg.log_dir, "rapprochement_annule", dossier=dossier_id, acteur=acteur,
          facture=facture_id, operation=operation_id, motif=motif)
    return {"ok": True, "facture_id": facture_id, "operation_id": operation_id}


def _totaux_par_devise(frais: list[Frais], factures: list[Facture]) -> dict[str, dict[str, Any]]:
    devises = sorted({_devise(f.devise) for f in frais} | {_devise(f.devise) for f in factures})
    resultat: dict[str, dict[str, Any]] = {}
    for devise in devises:
        frais_dev = [f for f in frais if _devise(f.devise) == devise]
        factures_dev = [f for f in factures if _devise(f.devise) == devise]

        def somme(items, champ):
            return _arrondi(sum((_decimal(getattr(i, champ)) for i in items), Decimal("0")))

        total_frais = somme(frais_dev, "montant")
        total_factures_client = somme([f for f in factures_dev if f.type_facture == "emisee"], "montant_ttc")
        categories = sorted({f.categorie for f in frais_dev})
        resultat[devise] = {
            "total_frais": total_frais,
            "total_avances": somme([f for f in frais_dev if f.avance_client], "montant"),
            "total_honoraires": somme([f for f in frais_dev if f.categorie == "honoraires_transitaire"], "montant"),
            "total_factures_client": total_factures_client,
            "total_factures_fournisseurs": somme([f for f in factures_dev if f.type_facture == "recue"], "montant_ttc"),
            "frais_payes": somme([f for f in frais_dev if f.statut_paiement == "paye"], "montant"),
            "frais_en_attente": somme([f for f in frais_dev if f.statut_paiement == "en_attente"], "montant"),
            "factures_payees": somme([f for f in factures_dev if f.statut_paiement == "payee"], "montant_ttc"),
            "factures_en_attente": somme([f for f in factures_dev if f.statut_paiement == "en_attente"], "montant_ttc"),
            "solde_restant": _arrondi(_decimal(total_factures_client) - _decimal(total_frais)),
            "rentabilite": _arrondi(_decimal(total_factures_client) - _decimal(total_frais)),
            "par_categorie": {cat: somme([f for f in frais_dev if f.categorie == cat], "montant")
                              for cat in categories},
            "par_statut_frais": {
                "payes": somme([f for f in frais_dev if f.statut_paiement == "paye"], "montant"),
                "en_attente": somme([f for f in frais_dev if f.statut_paiement == "en_attente"], "montant"),
                "en_retard": somme([f for f in frais_dev if f.statut_paiement == "en_retard"], "montant"),
            },
            "par_statut_factures": {
                "payees": somme([f for f in factures_dev if f.statut_paiement == "payee"], "montant_ttc"),
                "en_attente": somme([f for f in factures_dev if f.statut_paiement == "en_attente"], "montant_ttc"),
                "annulees": somme([f for f in factures_dev if f.statut_paiement == "annulee"], "montant_ttc"),
            },
        }
    return resultat


def resume_financier(cfg: Any, dossier_id: str) -> dict[str, Any]:
    frais = [f for f in BusinessStore(cfg.data_dir / "metier.sqlite3", "frais", Frais).values()
             if f.dossier_id == dossier_id]
    factures = [f for f in BusinessStore(cfg.data_dir / "metier.sqlite3", "facture", Facture).values()
                if f.dossier_id == dossier_id]
    par_devise = _totaux_par_devise(frais, factures)
    devises = sorted(par_devise)
    consolide = len(devises) == 1
    resume: dict[str, Any] = {
        "dossier_id": dossier_id,
        "devises": devises,
        "par_devise": par_devise,
        "consolide": consolide,
        "vide": not devises,
    }
    if consolide:
        resume.update(par_devise[devises[0]])
        resume["devise"] = devises[0]
    else:
        cles = ("total_frais", "total_avances", "total_honoraires", "total_factures_client",
                "total_factures_fournisseurs", "frais_payes", "frais_en_attente",
                "factures_payees", "factures_en_attente", "solde_restant", "rentabilite")
        for cle in cles:
            resume[cle] = None
        resume["devise"] = None
        resume["par_categorie"] = {}
        resume["par_statut_frais"] = {}
        resume["par_statut_factures"] = {}
        resume["avertissement"] = (
            "Aucun frais ni facture enregistré sur ce dossier." if not devises else
            "Plusieurs devises présentes : les totaux ne sont pas consolidés. "
            "Consultez par_devise ; aucune conversion de change n'est appliquée."
        )
    return resume
