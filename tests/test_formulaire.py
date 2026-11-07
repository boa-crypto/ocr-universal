"""Form builder du dossier — étape 12 du parcours.

**Ce que ces tests protègent.** La règle centrale du module : un champ n'existe
que si une valeur a réellement été extraite, ou si un humain l'a ajouté. Rien
n'est inventé pour « complérer » un formulaire, et un champ vide reste absent
plutôt que d'apparaître à vide.
"""
from __future__ import annotations

import pytest

from unocr.dossier import Dossier, DossierState
from unocr.formulaire import (
    FORM_VERSION,
    FormulaireStore,
    ajoute_champ,
    apercu_textuel,
    construit_depuis_dossier,
    renseigne,
    retire_champ,
)


class Piece:
    """Pièce minimale — le form builder n'a besoin que de ces trois attributs."""

    def __init__(self, job_id: str, filename: str, category: str) -> None:
        self.job_id = job_id
        self.filename = filename
        self.category = category


def dossier_simple() -> Dossier:
    return Dossier(
        id="dos_1", label="Import 2024-118", profile="importation",
        state=DossierState.EN_PREPARATION,
        pieces=[Piece("j1", "facture.pdf", "invoice"),
                Piece("j2", "bl.pdf", "bill_of_lading")],
    )


DOCUMENTS = [
    {"job_id": "j1", "filename": "facture.pdf", "category": "invoice", "champs": {
        "invoice_number": {"raw_value": "INV-2024-118",
                           "normalized_value": "INV-2024-118",
                           "status": "validated", "label": "N° facture"},
        "total_amount": {"raw_value": "1 250,00", "normalized_value": "1250.00",
                         "status": "detected", "label": "Montant total"},
        # un champ non détecté ne doit PAS créer d'entrée de formulaire
        "note_interne": {"raw_value": "", "normalized_value": "",
                         "status": "not_detected", "label": "Note"},
    }},
    {"job_id": "j2", "filename": "bl.pdf", "category": "bill_of_lading", "champs": {
        "invoice_number": {"raw_value": "INV-2024-118",
                           "normalized_value": "INV-2024-118",
                           "status": "detected", "label": "N° facture"},
        "gross_weight": {"raw_value": "12 000", "normalized_value": "12000",
                         "status": "detected", "label": "Poids brut"},
    }},
]


# ─────────────────────────── construction ───────────────────────────

def test_ne_cree_un_champ_que_si_une_valeur_existe() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    cles = [c.key for c in f.champs]
    assert "invoice_number" in cles
    assert "gross_weight" in cles
    # le champ non détecté ne doit pas apparaître, même à vide
    assert "note_interne" not in cles, "un champ sans valeur a été inventé"


def test_document_sans_champ_ne_cree_rien() -> None:
    f = construit_depuis_dossier(
        dossier_simple(),
        [{"job_id": "j3", "filename": "vide.pdf", "category": "generic", "champs": {}}])
    assert f.champs == [], "un document sans champ a produit des champs"
    assert "aucun champ" in apercu_textuel(f)


def test_provenance_de_chaque_champ_est_traced() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    poids = f.champ("gross_weight")
    assert poids is not None
    assert poids.origine == "extrait"
    assert poids.source_job == "j2"
    assert poids.source_field == "gross_weight"
    assert "bl.pdf" in poids.aide


def test_valeur_validee_est_marque_validee() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    # seul le champ validé par un humain est marqué valide
    assert f.champ("invoice_number").valide is True
    assert f.champ("total_amount").valide is False


def test_meme_champ_sur_deux_documents_est_fusionne_sans_perte() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    facture = [c for c in f.champs if c.key == "invoice_number"]
    assert len(facture) == 1, "le même champ ne doit pas être dupliqué"
    # mais la seconde occurrence est mentionnée, pas écrasée en silence
    assert "bl.pdf" in facture[0].aide


def test_type_indicatif_ne_bloque_jamais_la_valeur() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    assert f.champ("invoice_number").type == "identifier"
    assert f.champ("gross_weight").type == "number"
    assert f.champ("total_amount").type == "amount"
    # une valeur atypique reste acceptée
    etrange = construit_depuis_dossier(
        dossier_simple(),
        [{"job_id": "j1", "filename": "x.pdf", "category": "generic",
          "champs": {"zone_libre": {"raw_value": "libre", "status": "detected"}}}])
    assert etrange.champ("zone_libre").valeur == "libre"


def test_version_du_schema_est_declaree() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    assert f.version == FORM_VERSION


# ─────────────────────────── ajout et retrait humains ───────────────────────────

def test_ajout_humain_est_trace_comme_ajoute() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    champ = ajoute_champ(f, "reference_dossier", "Référence dossier",
                         required=True, aide="ajouté à la main")
    assert champ.origine == "ajoute"
    assert champ.source_job is None
    assert f.champ("reference_dossier") is not None


def test_ajout_d_une_cle_vide_est_refuse() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    with pytest.raises(ValueError, match="clé de champ vide"):
        ajoute_champ(f, "   ", "Vide")


def test_ajout_d_un_type_inconnu_est_refuse() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    with pytest.raises(ValueError, match="type inconnu"):
        ajoute_champ(f, "chose", "Chose", type="courriel")


def test_ajout_d_un_doublon_est_refuse() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    with pytest.raises(ValueError, match="déjà présent"):
        ajoute_champ(f, "invoice_number", "Doublon")


def test_renseigner_un_champ_inconnu_est_refuse() -> None:
    """Refuser évite qu'une faute de frappe crée un champ fantôme."""
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    with pytest.raises(ValueError, match="champ inconnu"):
        renseigne(f, "invoice_numbre", "INV-2024-118")


def test_renseigne_marque_la_validation_humaine() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    champ = renseigne(f, "total_amount", "1250.00", valide=True)
    assert champ.valeur == "1250.00"
    assert champ.valide is True


def test_retrait_ne_touche_pas_au_document() -> None:
    """Retirer un champ du formulaire n'est pas supprimer une donnée source."""
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    assert retire_champ(f, "gross_weight") is True
    assert f.champ("gross_weight") is None
    # la source est intacte : le champ peut être reconstruit
    reconstruit = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    assert reconstruit.champ("gross_weight") is not None
    assert retire_champ(f, "inexistant") is False


# ─────────────────────────── remplissage ───────────────────────────

def test_remplissage_est_compte_pas_estime() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    r = f.remplissage()
    assert r["total"] == 3
    assert r["remplis"] == 3
    assert r["valides"] == 1
    assert r["requis"] == 0
    assert r["complet"] is True


def test_champ_requis_manquant_empeche_le_complet() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    ajoute_champ(f, "reference_dossier", "Référence", required=True)
    r = f.remplissage()
    assert r["requis"] == 1
    assert r["requis_manquants"] == ["reference_dossier"]
    assert r["complet"] is False


def test_apercu_liste_les_champs_et_leurs_origines() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    ajoute_champ(f, "reference_dossier", "Référence dossier", required=True)
    texte = apercu_textuel(f)
    assert "invoice_number" in texte
    assert "extrait d'un document" in texte
    assert "ajouté par un humain" in texte
    assert "[requis]" in texte
    assert "0/4 champs remplis" not in texte   # 3 des 4 sont remplis


def test_apercu_signale_les_champs_vides() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    ajoute_champ(f, "reference_dossier", "Référence dossier", required=True)
    texte = apercu_textuel(f)
    # un champ requis vide est signalé, pas masqué
    assert "—" in texte
    assert "champ(s) requis manquant(s)" in texte


# ─────────────────────────── sérialisation ───────────────────────────

def test_as_dict_contient_la_provenance() -> None:
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    d = f.as_dict()
    assert d["version"] == FORM_VERSION
    assert d["dossier_id"] == "dos_1"
    assert "remplissage" in d
    poids = next(c for c in d["champs"] if c["key"] == "gross_weight")
    assert poids["origine"] == "extrait"
    assert poids["source_job"] == "j2"


# ─────────────────────────── persistance ───────────────────────────

def test_persistance_disque(tmp_path) -> None:
    store = FormulaireStore(tmp_path / "formulaires", log_dir=tmp_path / "logs")
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    store.sauve(f)
    relu = store.charge(f.formulaire_id)
    assert relu is not None
    assert [c.key for c in relu.champs] == [c.key for c in f.champs]
    assert relu.remplissage() == f.remplissage()
    assert relu.champ("gross_weight").source_job == "j2"


def test_persistance_conserve_les_ajouts_humains(tmp_path) -> None:
    store = FormulaireStore(tmp_path / "formulaires")
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    ajoute_champ(f, "reference_dossier", "Référence", required=True)
    renseigne(f, "total_amount", "1250.00", valide=True)
    store.sauve(f)
    relu = store.charge(f.formulaire_id)
    assert relu.champ("reference_dossier").origine == "ajoute"
    assert relu.champ("total_amount").valide is True


def test_liste_ignore_les_fichiers_illisibles(tmp_path) -> None:
    store = FormulaireStore(tmp_path / "formulaires")
    (tmp_path / "formulaires" / "casse.json").write_text("{pas du json", encoding="utf-8")
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    store.sauve(f)
    liste = store.liste()
    assert len(liste) == 1, "un fichier illisible ne doit pas faire échouer la liste"


def test_suppression_est_reelle(tmp_path) -> None:
    store = FormulaireStore(tmp_path / "formulaires")
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    store.sauve(f)
    assert store.supprime(f.formulaire_id) is True
    assert store.charge(f.formulaire_id) is None
    assert store.supprime(f.formulaire_id) is False


def test_identifiant_suspect_ne_sort_pas_du_repertoire(tmp_path) -> None:
    """Un identifiant avec des séparateurs doit rester dans le répertoire.

    Le chemin est assaini (séparateurs remplacés), donc aucun fichier ne peut
    être écrit ailleurs. On vérifie le résultat, pas le mécanisme.
    """
    store = FormulaireStore(tmp_path / "formulaires")
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    f.formulaire_id = "../evasion"
    chemin = store.sauve(f)
    assert chemin.parent == tmp_path / "formulaires"
    assert not (tmp_path / "evasion.json").exists()
    # et il reste rechargeable
    assert store.charge("../evasion") is not None


def test_identifiant_vide_ou_point_est_refuse(tmp_path) -> None:
    store = FormulaireStore(tmp_path / "formulaires")
    f = construit_depuis_dossier(dossier_simple(), DOCUMENTS)
    # « / » devient « _ » après assainissement : nom valide et sûr, pas refusé
    for identifiant in (".", ".."):
        f.formulaire_id = identifiant
        with pytest.raises(ValueError, match="invalide"):
            store.sauve(f)


# ─────────────── défauts d'extraction révélés par le form builder ───────────────
# Le formulaire met côte à côte toutes les valeurs extraites d'un dossier : deux
# défauts qui passaient inaperçus champ par champ deviennent visibles.

def test_quantite_ne_commence_pas_au_milieu_d_un_nombre() -> None:
    """« 12 000 KG » ne doit pas rendre « 000 » comme quantité."""
    from unocr.extract_fields import QTY_UNIT_RE

    m = QTY_UNIT_RE.search("GROSS WEIGHT: 12 000 KG")
    assert m is not None, "aucune quantité trouvée dans « 12 000 KG »"
    assert m.group(1) == "12 000", f"quantité tronquée : {m.group(1)!r}"
    assert m.group(2).upper() == "KG"


def test_quantite_sans_separateur_reste_lue() -> None:
    from unocr.extract_fields import QTY_UNIT_RE

    m = QTY_UNIT_RE.search("40 cartons")
    assert m is not None and m.group(1) == "40"


def test_liste_de_colisage_ne_capture_pas_le_mot_cle_suivant(tmp_path, tmp_cfg) -> None:
    """« PACKING LIST / Invoice ref: … » ne doit pas rendre « INVOICE ».

    Le champ `packing_list_number` doit rester vide quand la liste de
    colisage ne porte pas son propre numéro : mieux vaut rien qu'une valeur
    qui n'existe pas.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from parcours_fixtures import creer_fixtures

    from unocr.config import get_config
    from unocr.models import JobOptions
    from unocr.pipeline import Pipeline

    res = Pipeline(get_config()).process_file(
        creer_fixtures(tmp_path / "documents-parcours")["colisage"], JobOptions(export_formats=["json"]))
    valeur = res.fields["packing_list_number"].value
    assert valeur in (None, ""), f"mot-clé capturé comme numéro : {valeur!r}"


def test_poids_divergents_restent_justes_dans_le_formulaire(tmp_path, tmp_cfg) -> None:
    """Les valeurs du formulaire sont les vraies, pas des troncatures."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from parcours_fixtures import creer_fixtures

    from unocr.config import get_config
    from unocr.models import JobOptions
    from unocr.pipeline import Pipeline

    docs = creer_fixtures(tmp_path / "documents-parcours")
    valeurs = {}
    for role in ("bl", "colisage"):
        res = Pipeline(get_config()).process_file(
            docs[role], JobOptions(export_formats=["json"]))
        valeurs[role] = res.fields["gross_weight"].value
    assert valeurs["bl"] == "12000", f"poids du BL : {valeurs['bl']!r}"
    assert valeurs["colisage"] == "13500", f"poids du colisage : {valeurs['colisage']!r}"
    # et ces deux valeurs doivent rester divergentes : c'est l'incohérence
    # que le contrôle interdocumentaire doit remonter
    assert valeurs["bl"] != valeurs["colisage"]
