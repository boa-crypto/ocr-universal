"""Repères candidats sur copies synthétiques non officielles ; pas articles qualifiés."""

import hashlib
import json

import pytest
from test_customs_pdf_index import indexe as indexe
from test_customs_review import ADMIN, BASE
from test_customs_review import revue as revue

from unocr.customs_reference.pdf_markers import lire_page_indexee, reperer_articles

TEXTE = "😀 AVANT NON OFFICIEL\nArticle 1er. — Déclaration\nArt 4bis - Corps\nArt. 137. ó Disposition citée\nRenvoi à Art. 8 — pas début de ligne\nArt 340 quater- Autre texte\n<img src=x onerror=evil()>\n"


@pytest.fixture()
def marqueurs(indexe):
    r, f, _ = indexe
    data = json.loads(f.read_text())
    for document in data["documents"]:
        document["pages"][0]["texte"] = TEXTE
        document["pages"][0]["sha256_texte_utf8"] = hashlib.sha256(TEXTE.encode()).hexdigest()
    f.write_text(json.dumps(data, ensure_ascii=False))
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    reg = json.loads(r[2].read_text())
    for lot in reg["lots"]:
        if lot["id"] == "code_a":
            lot["index_pdf_sha256"] = sha
    r[2].write_text(json.dumps(reg))
    return r, f, sha


def test_reperes_litteraux_unicode_et_offsets(marqueurs):
    r, f, sha = marqueurs
    result = reperer_articles(r[1] / "code_a", f, sha, document_id="TEST_O")
    assert [v["numero_litteral"] for v in result["resultats"]] == [
        "1er",
        "4bis",
        "137",
        "340 quater",
    ]
    for v in result["resultats"]:
        assert TEXTE[v["debut"] : v["fin"]] == v["entete_litteral"]
        assert v["page_pdf"] == 1 and v["statut"] == "repere_candidat_non_valide"
        assert len(v["repere_id"]) == 64
    assert result["articles_localises_automatiquement"] is False
    assert result["reperes_detectes_automatiquement"] is True


def test_filtre_exact_pagination_et_pas_article_invente(marqueurs):
    r, f, sha = marqueurs
    result = reperer_articles(r[1] / "code_a", f, sha, numero="137", limite=1)
    assert result["total_correspondances"] == 3 and result["decalage_suivant"] == 1
    assert reperer_articles(r[1] / "code_a", f, sha, numero="8")["resultats"] == []
    assert reperer_articles(r[1] / "code_a", f, sha, numero="4 bis")["resultats"] == []
    assert reperer_articles(r[1] / "code_a", f, sha, document_id="ABSENT")["resultats"] == []


def test_lecture_indexee_fragment_borne_et_provenance(marqueurs):
    r, f, sha = marqueurs
    p = lire_page_indexee(r[1] / "code_a", f, sha, "TEST_O", 1, 20, 2)
    assert p["fragment"] == TEXTE[2:22] and p["decalage_suivant"] == 22
    assert p["sha256_texte_utf8"] == hashlib.sha256(TEXTE.encode()).hexdigest()
    assert p["index_sha256"] == sha and p["ocr_effectue"] is False
    assert p["publication_active"] is False and p["validation_juridique"] == "non_validee"


@pytest.mark.parametrize("document,page", [("ABSENT", 1), ("TEST_O", 3)])
def test_page_absente_404(marqueurs, document, page):
    r, _, _ = marqueurs
    response = r[0].get(
        BASE + "/lots/code_a/pdf-index-page",
        params={"document_id": document, "page": page},
        headers=ADMIN,
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "endpoint,params",
    [
        ("pdf-index-page", {"document_id": "TEST_O", "page": 0}),
        ("pdf-index-page", {"document_id": "TEST_O", "limit": 16001}),
        ("pdf-index-page", {"document_id": "TEST_O", "offset": -1}),
        ("pdf-article-markers", {"numero": " "}),
        ("pdf-article-markers", {"numero": "\x00"}),
        ("pdf-article-markers", {"limit": 0}),
    ],
)
def test_parametres_refuses(marqueurs, endpoint, params):
    r, _, _ = marqueurs
    assert (
        r[0].get(BASE + "/lots/code_a/" + endpoint, params=params, headers=ADMIN).status_code == 422
    )


@pytest.mark.parametrize(
    "endpoint,params",
    [("pdf-index-page", {"document_id": "TEST_O"}), ("pdf-article-markers", {"numero": "137"})],
)
def test_autorisation_et_source_index_obligatoires(marqueurs, endpoint, params):
    r, f, _ = marqueurs
    url = BASE + "/lots/code_a/" + endpoint
    assert r[0].get(url, params=params).status_code == 401
    response = r[0].get(url, params=params, headers=ADMIN)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert response.json()["resultat"]["lot_id"] == "code_a"
    f.write_text("{}")
    assert r[0].get(url, params=params, headers=ADMIN).status_code == 409


def test_lecture_offset_apres_fin_pas_de_texte_invente(marqueurs):
    r, f, sha = marqueurs
    p = lire_page_indexee(r[1] / "code_a", f, sha, "TEST_O", 1, 20, len(TEXTE) + 20)
    assert p["fragment"] == "" and p["decalage_suivant"] is None
