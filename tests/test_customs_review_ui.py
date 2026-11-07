"""Pont HTTP isolé vers le TestClient réel ; aucune fixture de production."""
import hashlib
import io
import json
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from reportlab.pdfgen import canvas

from tests import test_customs_review
from tests.test_customs_reference import snapshot
from tests.test_customs_subdivisions import subdivisions
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.review_export import analyser_export

revue = test_customs_review.revue


def test_interface_revue_sur_api_reelle(revue):
    root = Path(__file__).resolve().parents[1]
    if not shutil.which("node") or not (root / "node_modules/jsdom").is_dir():
        pytest.skip("Node et npm ci nécessaires au test navigateur JSDOM")
    client, racine, registre, cfg = revue
    # Réarchiver les mêmes transcriptions avec de vrais PDF techniques, sans
    # écraser les lots précédents ; le registre temporaire épingle ce nouveau lot.
    entrees = cfg.root / "pdf_ui"
    entrees.mkdir()
    meta = json.loads((racine / "code_a" / "metadata_original.json").read_text())
    for entree in meta["documents"]:
        tampon = io.BytesIO()
        pdf = canvas.Canvas(tampon)
        for numero in (1, 2):
            pdf.drawString(40, 700, f"FIXTURE NON OFFICIELLE TEXTE NATIF PAGE {numero}")
            pdf.showPage()
        pdf.save()
        contenu = tampon.getvalue()
        (entrees / entree["fichier_recu"]).write_bytes(contenu)
        entree["document"]["sha256"] = hashlib.sha256(contenu).hexdigest()
    metadata = entrees / "metadata.json"
    metadata.write_text(json.dumps(meta))
    transcription = entrees / "transcription.json"
    transcription.write_bytes((racine / "code_a" / "transcription_recue.json").read_bytes())
    preparer_code(transcription, metadata, racine / "code_pdf_ui")
    reg = json.loads(registre.read_text())
    # L'ancien lot reste intact et reçoit une identité de revue distincte ; le
    # lot Code principal pointe ensuite vers la nouvelle archive PDF technique.
    reg["lots"].append({"id":"code_b", "dossier":"code_a", "type_lot":"code",
                        "manifest_sha256":hashlib.sha256((racine / "code_a" / "manifest.json").read_bytes()).hexdigest()})
    for entree in reg["lots"]:
        if entree["id"] == "code_a":
            entree["dossier"] = "code_pdf_ui"
            entree["manifest_sha256"] = hashlib.sha256((racine / "code_pdf_ui" / "manifest.json").read_bytes()).hexdigest()
    registre.write_text(json.dumps(reg))
    entrees_tarif = cfg.root / "subdivisions_ui"
    entrees_tarif.mkdir()
    source = entrees_tarif / "source.json"
    lignes = json.loads((racine / "tarif_a" / "source_recue.json").read_text())
    lignes[0]["code_subdivision_nationale"] = "010100000"
    source.write_text(json.dumps(lignes))
    meta = json.loads((racine / "tarif_a" / "metadata_original.json").read_text())
    meta["lot"]["subdivisions_nationales"] = subdivisions()
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata = entrees_tarif / "metadata.json"
    metadata.write_text(json.dumps(meta))
    preparer_tarif(source, metadata, racine / "tarif_sub_ui")
    reg = json.loads(registre.read_text())
    for entree in reg["lots"]:
        if entree["id"] == "tarif_a":
            entree["dossier"] = "tarif_sub_ui"
            entree["manifest_sha256"] = hashlib.sha256((racine / "tarif_sub_ui" / "manifest.json").read_bytes()).hexdigest()
    registre.write_text(json.dumps(reg))
    cfg.web_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "web/index.html", cfg.web_dir / "index.html")
    avant = snapshot(racine)

    class Pont(BaseHTTPRequestHandler):
        def do_GET(self):
            reponse = client.get(self.path, headers=dict(self.headers))
            self.send_response(reponse.status_code)
            for cle,valeur in reponse.headers.items():
                if cle.lower() not in {"connection", "transfer-encoding"}:
                    self.send_header(cle,valeur)
            self.end_headers()
            self.wfile.write(reponse.content)

        def log_message(self, *args):
            pass

    serveur = ThreadingHTTPServer(("0.0.0.0", 0), Pont)
    thread = Thread(target=serveur.serve_forever, daemon=True)
    thread.start()
    try:
        resultat = subprocess.run(
            ["node", "tests/ui_customs_review_integration.js", f"http://127.0.0.1:{serveur.server_port}"],
            cwd=root, capture_output=True, text=True, timeout=30,
        )
        assert resultat.returncode == 0, resultat.stdout + resultat.stderr
        exports = [ligne.removeprefix("EXPORT_REEL_JSON=") for ligne in resultat.stdout.splitlines()
                   if ligne.startswith("EXPORT_REEL_JSON=")]
        assert len(exports) == 12
        copies = [v.removeprefix("PDF_SOURCE_SHA256=") for v in resultat.stdout.splitlines() if v.startswith("PDF_SOURCE_SHA256=")]
        assert copies == [hashlib.sha256((racine / "code_pdf_ui/document_0001.pdf").read_bytes()).hexdigest()]
        for texte in exports:
            constat = analyser_export(texte.encode("utf-8"))
            assert constat["statut"] == "structure_compatible"
            assert constat["authenticite_verifiee"] is False
        assert json.loads(exports[0])["resultat"]["type_rapport"] == "lecture_page_pdf_recu"
        assert snapshot(racine) == avant
    finally:
        serveur.shutdown()
        serveur.server_close()
        thread.join(timeout=5)
