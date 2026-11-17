"""Index de pages sur fixtures NON OFFICIELLES ; origine des textes non attestée."""

import hashlib
import json

import pytest
from test_customs_review import ADMIN, BASE
from test_customs_review import revue as revue

from unocr.customs_reference.legal_comparison import charger_lot_code
from unocr.customs_reference.pdf_index import DocumentIndexe, IndexPDF, PageNative, rechercher_pages


@pytest.fixture()
def indexe(revue):
    lot, _ = charger_lot_code(revue[1] / "code_a")
    manifest = hashlib.sha256((revue[1] / "code_a/manifest.json").read_bytes()).hexdigest()
    documents = []
    for doc in lot.documents:
        pages = []
        for n, text in enumerate(
            [
                "FIXTURE NON OFFICIELLE douanes <img src=x onerror=evil()>",
                "Déclaration مادة NON OFFICIELLE",
            ],
            1,
        ):
            pages.append(
                PageNative(
                    page=n, texte=text, sha256_texte_utf8=hashlib.sha256(text.encode()).hexdigest()
                )
            )
        documents.append(DocumentIndexe(document_id=doc.id, pdf_sha256=doc.sha256, pages=pages))
    index = IndexPDF(
        manifest_lot_sha256=manifest, version_extracteur="TEST_NON_OFFICIEL", documents=documents
    )
    dossier = revue[1] / "index_pdf"
    dossier.mkdir()
    fichier = dossier / "code_a.json"
    fichier.write_bytes(index.model_dump_json().encode())
    sha = hashlib.sha256(fichier.read_bytes()).hexdigest()
    reg = json.loads(revue[2].read_text())
    for entree in reg["lots"]:
        if entree["id"] == "code_a":
            entree["index_pdf_sha256"] = sha
    revue[2].write_text(json.dumps(reg))
    return revue, fichier, sha


def test_recherche_paginee_normalisee_pas_articles(indexe):
    r, f, sha = indexe
    resultat = rechercher_pages(r[1] / "code_a", f, sha, "declaration", limite=1)
    assert resultat["total_correspondances"] == 3 and resultat["decalage_suivant"] == 1
    assert resultat["resultats"][0]["page_pdf"] == 2
    assert (
        resultat["ocr_effectue"] is False
        and resultat["articles_localises_automatiquement"] is False
    )
    assert resultat["index_sha256"] == sha
    assert resultat["resultats"][0]["extraits"]
    dernier = rechercher_pages(r[1] / "code_a", f, sha, "declaration", limite=1, decalage=2)
    assert dernier["decalage_suivant"] is None


def test_filtre_document_arabe_et_tous_termes_meme_page(indexe):
    r, f, sha = indexe
    lot, _ = charger_lot_code(r[1] / "code_a")
    resultat = rechercher_pages(
        r[1] / "code_a", f, sha, "déclaration مادة", document_id=lot.documents[0].id
    )
    assert resultat["total_correspondances"] == 1
    assert (
        rechercher_pages(r[1] / "code_a", f, sha, "douanes déclaration")["total_correspondances"]
        == 0
    )
    assert (
        rechercher_pages(r[1] / "code_a", f, sha, "douanes", document_id="ABSENT")[
            "total_correspondances"
        ]
        == 0
    )


def test_api_auth_index_source_et_cache(indexe):
    r, _, _ = indexe
    url = BASE + "/lots/code_a/pdf-search?q=douanes"
    assert r[0].get(url).status_code == 401
    response = r[0].get(url, headers=ADMIN)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert response.json()["resultat"]["lot_id"] == "code_a"
    assert r[0].get(BASE + "/lots/tarif_a/pdf-search?q=douanes", headers=ADMIN).status_code == 422
    reg = json.loads(r[2].read_text())
    reg["reviseurs"] = []
    r[2].write_text(json.dumps(reg))
    assert r[0].get(url, headers=ADMIN).status_code == 403


def test_index_absent_non_epingle_refuse(revue):
    assert (
        revue[0].get(BASE + "/lots/code_a/pdf-search?q=douanes", headers=ADMIN).status_code == 409
    )


@pytest.mark.parametrize("params", ["q=", "q=!!!", "q=douanes&limit=0", "q=douanes&offset=-1"])
def test_parametres_refuses(indexe, params):
    r, _, _ = indexe
    assert r[0].get(BASE + "/lots/code_a/pdf-search?" + params, headers=ADMIN).status_code == 422


def test_index_modifie_meme_si_hash_interne_recalcule(indexe):
    r, f, sha = indexe
    index = json.loads(f.read_text())
    p = index["documents"][0]["pages"][0]
    p["texte"] = "TEXTE FORGE NON OFFICIEL"
    p["sha256_texte_utf8"] = hashlib.sha256(p["texte"].encode()).hexdigest()
    f.write_text(json.dumps(index))
    with pytest.raises(ValueError):
        rechercher_pages(r[1] / "code_a", f, sha, "douanes")
    assert r[0].get(BASE + "/lots/code_a/pdf-search?q=douanes", headers=ADMIN).status_code == 409


def test_source_modifiee_refusee(indexe):
    r, _, _ = indexe
    (r[1] / "code_a/document_0001.pdf").write_bytes(b"%PDF ALTERE")
    assert r[0].get(BASE + "/lots/code_a/pdf-search?q=douanes", headers=ADMIN).status_code == 409


def test_index_lie_a_autre_manifest_refuse_meme_epingle(indexe):
    r, f, _ = indexe
    data = json.loads(f.read_text())
    data["manifest_lot_sha256"] = "0" * 64
    f.write_text(json.dumps(data))
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        rechercher_pages(r[1] / "code_a", f, sha, "douanes")


def test_page_et_empreinte_incoherentes_refusees():
    with pytest.raises(ValueError):
        PageNative(page=1, texte="texte", sha256_texte_utf8="0" * 64)
    p = PageNative(page=2, texte="", sha256_texte_utf8=hashlib.sha256(b"").hexdigest())
    with pytest.raises(ValueError):
        DocumentIndexe(document_id="TEST", pdf_sha256="0" * 64, pages=[p])


def test_interface_sur_api_http(indexe):
    import shutil
    import subprocess
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from pathlib import Path
    from threading import Thread
    root = Path(__file__).resolve().parents[1]
    if not shutil.which("node") or not (root/"node_modules/jsdom").is_dir():
        pytest.skip("Node et jsdom requis")
    client=indexe[0][0]
    class Pont(BaseHTTPRequestHandler):
        def do_GET(self):
            r=client.get(self.path,headers=dict(self.headers))
            self.send_response(r.status_code)
            for k,v in r.headers.items():
                if k.lower() not in {"connection","transfer-encoding"}:
                    self.send_header(k,v)
            self.end_headers()
            self.wfile.write(r.content)
        def log_message(self,*args):
            pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Pont)
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        for script in ["tests/ui_customs_legal_pages.js","tests/ui_customs_legal_pages_integration.js"]:
            r=subprocess.run(["node",script,f"http://127.0.0.1:{server.server_port}"],cwd=root,capture_output=True,text=True,timeout=30)
            assert r.returncode==0,r.stdout+r.stderr
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_construction_sur_vrai_pdf_technique_et_refus_ecrasement(tmp_path):
    from reportlab.pdfgen import canvas

    from unocr.customs_reference.legal_importer import preparer_code
    from unocr.customs_reference.pdf_index import construire_index
    pdf=tmp_path/"technique.pdf"
    c=canvas.Canvas(str(pdf))
    c.drawString(30,700,"FIXTURE NON OFFICIELLE douanes")
    c.save()
    doc={"id":"TEST_RECU","titre":"FIXTURE NON OFFICIELLE","url":None,"organisme":"TEST",
         "version_source":"TEST","sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),"format":"pdf",
         "nature_document":"compilation","provenance":"piece_jointe_utilisateur","nom_fichier_recu":pdf.name}
    metadata=tmp_path/"metadata.json"
    metadata.write_text(json.dumps({"documents":[{"fichier_recu":pdf.name,"document":doc}]}))
    transcription=tmp_path/"texte.json"
    transcription.write_text('{"articles":[],"relations":[]}')
    lot=tmp_path/"lot"
    preparer_code(transcription,metadata,lot)
    sortie=tmp_path/"index.json"
    r=construire_index(lot,sortie)
    assert r["pages"]==1
    resultat=rechercher_pages(lot,sortie,r["index_sha256"],"douanes")
    assert resultat["total_correspondances"]==1 and resultat["resultats"][0]["extraits"]
    avant=sortie.read_bytes()
    with pytest.raises(FileExistsError):
        construire_index(lot,sortie)
    assert sortie.read_bytes()==avant
