"""Classification documentaire (étape 4 du parcours).

**Pourquoi ces tests.** Le classifieur note des indices textuels explicites. Ce
qui est vérifié ici, ce n'est pas « il devine bien » mais :

- la confiance reflète des indices **réellement matchés** (aucun pourcentage
  inventé) ;
- un document sans indice part en révision au lieu d'être forcé dans une
  catégorie ;
- les catégories déclarées sans indice sont visibles comme désactivées ;
- une correction humaine est traçable ;
- les profils d'extraction existants sont réutilisés, pas dupliqués.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from unocr.classification import (
    ABSORPTION,
    CONFIANCE_MAX,
    SEUIL_ACCEPTATION,
    SEUIL_REVISION,
    DocumentClassifier,
    classification_manuelle,
)

RACINE = Path(__file__).resolve().parent.parent
PROFILES = RACINE / "profiles"

FACTURE = """COMMERCIAL INVOICE
Invoice No: 2024-118
Date: 12/03/2024
Seller: ACME SARL
INCOterm: FOB Alger
TOTAL AMOUNT: 1 250,50 EUR
"""

BL = """BILL OF LADING
B/L No: ACMU1234567
SHIPPER: ACME SARL
CONSIGNEE: Buyer Ltd
NOTIFY PARTY: Notify SA
PORT OF LOADING: DZALG
PORT OF DISCHARGE: FRMRS
VESSEL: MV STAR
VOYAGE: 12E
CONTAINER: MSCU1234567
"""

COLISAGE = """PACKING LIST
Invoice ref: 2024-118
GROSS WEIGHT: 12 000 KG
NET WEIGHT: 11 500 KG
CARTONS: 40
"""

ORIGINE = """CERTIFICATE OF ORIGIN
COUNTRY OF ORIGIN: ALGERIA
Invoice ref: 2024-118
"""


@pytest.fixture(scope="module")
def classifier() -> DocumentClassifier:
    return DocumentClassifier(profiles_dir=PROFILES)


# ───────────────────────────── classification ───────────────────────────────

def test_reconnait_une_facture(classifier) -> None:
    r = classifier.classify(FACTURE)
    assert r.category == "invoice"
    assert r.confidence >= SEUIL_ACCEPTATION
    assert not r.needs_review
    assert r.evidence, "une classification sans preuve n'est pas acceptable"
    assert classifier.profil_pour("invoice") == "invoice"


def test_reconnait_un_connaissement(classifier) -> None:
    r = classifier.classify(BL)
    assert r.category == "bill_of_lading"
    assert r.confidence >= SEUIL_ACCEPTATION
    assert classifier.profil_pour("bill_of_lading") == "port_bl"


def test_reconnait_une_liste_de_colisage(classifier) -> None:
    r = classifier.classify(COLISAGE)
    assert r.category == "packing_list"
    assert r.confidence >= SEUIL_ACCEPTATION


def test_reconnait_un_certificat_dorigine(classifier) -> None:
    r = classifier.classify(ORIGINE)
    assert r.category == "certificate_of_origin"
    assert r.confidence >= SEUIL_ACCEPTATION


def test_document_sans_indice_part_en_revision(classifier) -> None:
    """Un texte quelconque ne doit jamais être forcé dans une catégorie."""
    r = classifier.classify("bonjour ceci est un texte sans aucun indice métier")
    assert r.category == "unknown"
    assert r.needs_review is True
    assert r.confidence == 0.0
    assert r.reason


def test_texte_vide_est_inconnu(classifier) -> None:
    r = classifier.classify("")
    assert r.category == "unknown"
    assert r.needs_review is True


def test_un_mot_isole_ne_suffit_pas(classifier) -> None:
    """« INVOICE » seul : confiance faible → révision, pas d'acceptation."""
    r = classifier.classify("INVOICE")
    assert r.confidence < SEUIL_ACCEPTATION
    assert r.needs_review is True


# ───────────────────────────── confiance et preuves ─────────────────────────

def test_la_confiance_est_plafonnee(classifier) -> None:
    """Même un document qui matche tout ne atteint jamais 100 %."""
    texte = BL + "\nBILL OF LADING again\nSHIPPER: X\nCONSIGNEE: Y\n"
    r = classifier.classify(texte)
    assert r.confidence <= CONFIANCE_MAX
    assert r.confidence < 1.0


def test_chaque_preuve_cite_le_texte_matche(classifier) -> None:
    r = classifier.classify(BL)
    for preuve in r.evidence:
        assert preuve["matched_text"], "preuve sans texte réellement matché"
        assert preuve["weight"] > 0
        assert preuve["kind"] in ("distinctive", "complementary")


def test_les_indices_de_profil_sont_complementaires(classifier) -> None:
    """Les motifs hérités des profils ne doivent pas noyer la confiance."""
    cat = classifier.categories["bill_of_lading"]
    complementaires = [i for i in cat.indicateurs if i.poids < 1.0]
    distinctifs = [i for i in cat.indicateurs if i.poids >= 1.0]
    assert distinctifs, "une catégorie doit garder des indices distinctifs"
    assert complementaires, "les motifs de profil doivent servir de preuves"
    assert cat.poids_principal() == sum(i.poids for i in distinctifs)


def test_alternatives_proposees(classifier) -> None:
    """Un document à cheval sur deux catégories doit dire laquelle est la 2e."""
    texte = BL + "\nCMR reference\nLETTRE DE TRANSPORT jointe\n"
    r = classifier.classify(texte)
    assert r.category == "bill_of_lading"
    ids = [a["category"] for a in r.alternatives]
    assert "transport_document" in ids, f"alternatives = {ids}"


def test_ambiguite_signalee(classifier) -> None:
    """Deux catégories au coude-à-coude doivent déclencher la révision."""
    # connaissement + document de transport, indices équilibrés
    texte = ("BILL OF LADING\nB/L No: X1\nSHIPPER: A\nCONSIGNEE: B\n"
             "NOTIFY PARTY: C\nPORT OF LOADING: DZALG\nVESSEL: V\nVOYAGE: 1\n"
             "CMR 123456\nAIR WAYBILL 999\nLETTRE DE TRANSPORT\n")
    r = classifier.classify(texte)
    assert r.needs_review is True
    assert "ambigu" in r.reason.lower()


# ───────────────────────────── seuils documentés ───────────────────────────

def test_seuils_sont_coherents() -> None:
    assert 0 < SEUIL_REVISION < SEUIL_ACCEPTATION < CONFIANCE_MAX
    assert ABSORPTION > 0


# ─────────────────────── catégories désactivées / manuelles ────────────────

def test_categories_sans_indice_sont_visibles(classifier) -> None:
    """« divers » et « inconnu » sont des états, pas des catégories devinées."""
    desactivees = {d["id"] for d in classifier.disabled_categories()}
    assert "unknown" in desactivees
    assert "misc" in desactivees


def test_correction_manuelle_traçable() -> None:
    r = classification_manuelle("invoice", "utilisateur.test")
    assert r.manual is True
    assert r.corrected_by == "utilisateur.test"
    assert r.needs_review is False
    assert r.confidence == 1.0
    assert r.as_dict()["manual"] is True


def test_correction_manuelle_refuse_une_categorie_inconnue() -> None:
    with pytest.raises(ValueError):
        classification_manuelle("licence_de_plongee", "qui.que.soit")


def test_categories_utilisateur_chargees(tmp_path) -> None:
    """Un type ajouté par l'utilisateur doit devenir classable."""
    types = tmp_path / "types"
    types.mkdir()
    (types / "mon_type.json").write_text(json.dumps({
        "id": "mon_type", "label": "Mon type métier",
        "indicators": [{"pattern": "DOCUMENT MAGIQUE", "weight": 3.0,
                        "label": "phrase magique"}],
    }), encoding="utf-8")
    (types / "vide.json").write_text(json.dumps({
        "id": "sans_indice", "label": "Sans indice",
    }), encoding="utf-8")

    c = DocumentClassifier(profiles_dir=PROFILES, user_types_dir=types)
    r = c.classify("DOCUMENT MAGIQUE\nsuite du texte")
    assert r.category == "mon_type"
    assert r.confidence >= SEUIL_ACCEPTATION
    desactivees = {d["id"] for d in c.disabled_categories()}
    assert "sans_indice" in desactivees, "une catégorie sans indice doit être désactivée"


def test_profil_illisible_ne_casse_pas_le_classifieur(tmp_path) -> None:
    (tmp_path / "casse.json").write_text("{pas du json", encoding="utf-8")
    c = DocumentClassifier(profiles_dir=tmp_path)
    r = c.classify("INVOICE No 1\nTOTAL AMOUNT: 10 EUR\nINCOterm: FOB\n")
    assert r.category in ("invoice", "unknown")


def test_resultat_serialisable(classifier) -> None:
    r = classifier.classify(FACTURE)
    d = r.as_dict()
    assert set(d) >= {"category", "confidence", "evidence", "needs_review",
                      "classifier_version", "manual"}
    json.dumps(d, ensure_ascii=False)      # ne doit pas lever
