"""Fixtures NON OFFICIELLES temporaires : ni vrais PDF JO, ni corpus juridique."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_customs_reference import snapshot
from unocr.cli import main
from unocr.customs_reference.comparison import charger_lot
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.legal_models import CodeDocumentaireBatch, MetadataCode


def fichiers_code(root):
    documents, articles = [], []
    for suffixe, role, nature, date in (("O", "code_original", "originale", "2000-01-01"),
                                       ("M", "acte_modificatif", "modificative", "2001-01-01"),
                                       ("C", "compilation", "consolidee_provisoire", "2002-01-01")):
        nom = "FIXTURE_NON_OFFICIELLE_" + suffixe + ".pdf"
        # Signature de test uniquement : le lecteur ne prétend pas qualifier PDF.
        contenu = b"%PDF-1.7\nFIXTURE NON OFFICIELLE " + suffixe.encode() + b"\n%%EOF\n"
        (root / nom).write_bytes(contenu)
        identifiant = "TEST_" + suffixe
        documents.append({"fichier_recu": nom, "document": {
            "id": identifiant, "titre": "FIXTURE NON OFFICIELLE " + suffixe,
            "url": "https://www.joradp.dz/TEST_NON_OFFICIEL/" + nom,
            "organisme": "FIXTURE NON OFFICIELLE", "version_source": "TEST_" + suffixe,
            "format": "pdf", "nature_document": role, "date_publication": date,
            "sha256": hashlib.sha256(contenu).hexdigest(),
        }})
        numero = "7" if suffixe == "M" else "5 bis"
        articles.append({"id": identifiant + "_A", "numero_article": numero,
                         "version_juridique": "TEST_" + suffixe, "nature_version": nature,
                         "texte_integral": "FIXTURE NON OFFICIELLE " + suffixe,
                         "hierarchie": [{"niveau": "texte_legislatif", "identifiant": identifiant},
                                        {"niveau": "article", "identifiant": numero}],
                         "reference": {"source_id": identifiant, "localisateur": "FIXTURE page 1"}})
    articles[0]["texte_arabe"] = "نص تجريبي غير رسمي"
    articles[1]["articles_lies"] = [articles[0]["id"]]
    relation = {"id": "TEST_RELATION", "origine_id": articles[1]["id"], "cible_id": articles[0]["id"],
                "type_relation": "modifie", "justification": "FIXTURE NON OFFICIELLE : preuve déclarée seulement",
                "reference": {"source_id": "TEST_M", "localisateur": "FIXTURE page 1, disposition modificative"}}
    transcription, metadata = root / "transcription_NON_OFFICIELLE.json", root / "metadata_NON_OFFICIELLE.json"
    transcription.write_text(json.dumps({"articles": articles, "relations": [relation]}, ensure_ascii=False))
    metadata.write_text(json.dumps({"documents": documents}))
    return transcription, metadata


def modifier(path, fonction):
    objet = json.loads(path.read_text())
    fonction(objet)
    path.write_text(json.dumps(objet, ensure_ascii=False))


def test_plan_sans_ecriture_et_comptage_non_completude(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    avant = snapshot(tmp_path)
    rapport = preparer_code(transcription, metadata)
    assert snapshot(tmp_path) == avant
    assert rapport["documents_recus"] == rapport["articles_declares"] == 3
    assert rapport["articles_par_nature"] == {"originale": 1, "modificative": 1, "consolidee_provisoire": 1}
    assert rapport["relations_declarees"] == 1
    assert rapport["completude_reglementaire"] == "non_etablie"
    assert rapport["transcription_verification"] == "non_verifiee"
    assert rapport["publication_active"] is False
    assert rapport["restitution_juridique_a_date"] is False
    assert rapport["ecrit"] is False


def test_archive_octets_exactes_sources_separees_manifest_et_aucun_ecrasement(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    sortie = tmp_path / "lot"
    rapport = preparer_code(transcription, metadata, sortie)
    assert rapport["ecrit"] is True
    assert (sortie / "transcription_recue.json").read_bytes() == transcription.read_bytes()
    assert (sortie / "metadata_original.json").read_bytes() == metadata.read_bytes()
    manifest = json.loads((sortie / "manifest.json").read_text())
    assert manifest["date_importation"].endswith("+00:00")
    for doc in manifest["documents"]:
        assert (sortie / doc["fichier_archive"]).read_bytes() == (tmp_path / doc["nom_recu"]).read_bytes()
    for nom, sha in manifest["fichiers_sha256"].items():
        assert hashlib.sha256((sortie / nom).read_bytes()).hexdigest() == sha
    lot = json.loads((sortie / "lot_code.json").read_text())
    assert lot["articles"][0]["numero_article"] == "5 bis"
    assert lot["articles"][0]["texte_arabe"] == "نص تجريبي غير رسمي"
    assert all(a["validation_juridique"] == "non_validee" for a in lot["articles"])
    avant = snapshot(tmp_path)
    with pytest.raises(FileExistsError):
        preparer_code(transcription, metadata, sortie)
    assert snapshot(tmp_path) == avant
    with pytest.raises(ValueError):
        charger_lot(sortie)  # Aucun mélange avec les lots tarifaires.


def test_archive_sans_article_sans_completude_inventee(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    transcription.write_text('{"articles": [], "relations": []}')
    rapport = preparer_code(transcription, metadata, tmp_path / "lot")
    assert rapport["articles_declares"] == 0
    assert rapport["documents_sans_article_transcrit"] == ["TEST_C", "TEST_M", "TEST_O"]
    assert rapport["completude_reglementaire"] == "non_etablie"


@pytest.mark.parametrize("champ,valeur", [
    ("texte_integral", " "), ("version_juridique", " "), ("numero_article", 5),
    ("nature_version", "consolidee_provisoire"), ("validation_juridique", "validee"),
    ("hierarchie", []), ("texte_modificatif", "FUSION INTERDITE"),
    ("texte_origine", "AUTRE TEXTE"), ("date_entree_vigueur", "2001-01-02"),
    ("texte_arabe", " "), ("articles_lies", ["INCONNU"]),
    ("historique_modifications", [{"source_id": "INCONNU", "localisateur": "page 1"}]),
])
def test_article_invalide_refuse_avant_creation(tmp_path, champ, valeur):
    transcription, metadata = fichiers_code(tmp_path)
    def changer(brut):
        brut["articles"][0][champ] = valeur
        if champ == "date_entree_vigueur":
            brut["articles"][0]["date_fin_validite"] = "2000-01-01"
    modifier(transcription, changer)
    with pytest.raises(ValueError):
        preparer_code(transcription, metadata, tmp_path / "sortie")
    assert not (tmp_path / "sortie").exists()


@pytest.mark.parametrize("champ,valeur", [
    ("type_relation", "similaire"), ("origine_id", "INCONNU"), ("cible_id", "TEST_M_A"),
    ("justification", " "), ("reference", {"source_id": "TEST_O", "localisateur": "page 1"}),
    ("reference", {"source_id": "TEST_M", "localisateur": " "}),
    ("validation_juridique", "validee"), ("origine_id", "TEST_C_A"),
])
def test_relation_sans_preuve_coherente_refusee(tmp_path, champ, valeur):
    transcription, metadata = fichiers_code(tmp_path)
    modifier(transcription, lambda brut: brut["relations"][0].update({champ: valeur}))
    with pytest.raises(ValueError):
        preparer_code(transcription, metadata)


@pytest.mark.parametrize("defaut", ["article_id", "article_version", "source_id", "relation_id", "preuve", "lien"])
def test_doublons_refuses(tmp_path, defaut):
    transcription, metadata = fichiers_code(tmp_path)
    def changer(brut):
        if defaut in {"article_id", "article_version"}:
            article = copy.deepcopy(brut["articles"][0])
            if defaut == "article_version":
                article["id"] += "_AUTRE"
            brut["articles"].append(article)
        elif defaut == "lien":
            brut["articles"][1]["articles_lies"] *= 2
        else:
            relation = copy.deepcopy(brut["relations"][0])
            if defaut == "preuve":
                relation["id"] += "_AUTRE"
            brut["relations"].append(relation)
    if defaut == "source_id":
        modifier(metadata, lambda brut: brut["documents"].append(copy.deepcopy(brut["documents"][0])))
    else:
        modifier(transcription, changer)
    with pytest.raises(ValueError):
        preparer_code(transcription, metadata)


@pytest.mark.parametrize("defaut", ["source", "localisateur", "hierarchie_numero", "hierarchie_ordre", "historique", "modif_fusion", "compilation_fusion", "date_abrogation"])
def test_structure_et_separation_juridique(tmp_path, defaut):
    transcription, metadata = fichiers_code(tmp_path)
    def changer(brut):
        article = brut["articles"][0]
        if defaut == "source":
            article["reference"]["source_id"] = "ABSENT"
        elif defaut == "localisateur":
            article["reference"]["localisateur"] = " "
        elif defaut == "hierarchie_numero":
            article["hierarchie"][1]["identifiant"] = "6"
        elif defaut == "hierarchie_ordre":
            article["hierarchie"].reverse()
        elif defaut == "historique":
            article["historique_modifications"] = [article["reference"]]
        elif defaut == "modif_fusion":
            brut["articles"][1]["texte_origine"] = article["texte_integral"]
        elif defaut == "compilation_fusion":
            brut["articles"][2]["texte_modificatif"] = "FUSION"
        else:
            article.update(date_entree_vigueur="2001-01-01", date_abrogation="2000-01-01")
    modifier(transcription, changer)
    with pytest.raises(ValueError):
        preparer_code(transcription, metadata)


def test_historique_declare_sans_consolidation_et_renvois_reciproques(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    def changer(brut):
        brut["articles"][0]["historique_modifications"] = [{"source_id": "TEST_M", "localisateur": "FIXTURE page 1"}]
        brut["relations"][0]["type_relation"] = "renvoie_a"
        retour = copy.deepcopy(brut["relations"][0])
        retour.update(id="TEST_RETOUR", origine_id="TEST_O_A", cible_id="TEST_M_A", reference=brut["articles"][0]["reference"])
        brut["relations"].append(retour)
    modifier(transcription, changer)
    assert preparer_code(transcription, metadata)["relations_declarees"] == 2


def test_chronologie_publication_contradictoire(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    modifier(metadata, lambda brut: brut["documents"][1]["document"].update(date_publication="1999-01-01"))
    with pytest.raises(ValueError, match="Chronologie"):
        preparer_code(transcription, metadata)


def test_cycle_modifications_refuse_sans_recursion(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    def changer(brut):
        article = copy.deepcopy(brut["articles"][1])
        article.update(id="TEST_M_B", numero_article="6", articles_lies=[])
        article["hierarchie"][1]["identifiant"] = "6"
        brut["articles"].append(article)
        brut["relations"][0]["cible_id"] = "TEST_M_B"
        brut["articles"][1]["articles_lies"] = []
        retour = copy.deepcopy(brut["relations"][0])
        retour.update(id="TEST_RETOUR", origine_id="TEST_M_B", cible_id="TEST_M_A")
        brut["relations"].append(retour)
    modifier(transcription, changer)
    with pytest.raises(ValueError, match="Cycle"):
        preparer_code(transcription, metadata)


@pytest.mark.parametrize("defaut", ["hash", "signature", "absent", "symlink", "traversal", "absolu", "windows", "fichier_partage", "format"])
def test_documents_opaques_refuses(tmp_path, defaut):
    transcription, metadata = fichiers_code(tmp_path)
    meta = json.loads(metadata.read_text())
    entree = meta["documents"][0]
    pdf = tmp_path / entree["fichier_recu"]
    if defaut in {"hash", "signature"}:
        pdf.write_bytes(b"PAS UN PDF, FIXTURE NON OFFICIELLE")
        if defaut == "signature":
            entree["document"]["sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    elif defaut == "absent":
        pdf.unlink()
    elif defaut == "symlink":
        pdf.unlink()
        pdf.symlink_to(tmp_path / meta["documents"][1]["fichier_recu"])
    elif defaut in {"traversal", "absolu", "windows"}:
        entree["fichier_recu"] = {"traversal": "../exterieur.pdf", "absolu": "/etc/passwd", "windows": "C:\\exterieur.pdf"}[defaut]
    elif defaut == "format":
        entree["document"]["format"] = "json"
    else:
        meta["documents"][1]["fichier_recu"] = entree["fichier_recu"]
        meta["documents"][1]["document"]["sha256"] = entree["document"]["sha256"]
    metadata.write_text(json.dumps(meta))
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError):
        preparer_code(transcription, metadata, tmp_path / "lot")
    assert snapshot(tmp_path) == avant


def test_doublons_octets_signales_pas_silencieusement_fusionnes(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    meta = json.loads(metadata.read_text())
    premiere, seconde = meta["documents"][:2]
    (tmp_path / seconde["fichier_recu"]).write_bytes((tmp_path / premiere["fichier_recu"]).read_bytes())
    seconde["document"]["sha256"] = premiere["document"]["sha256"]
    metadata.write_text(json.dumps(meta))
    rapport = preparer_code(transcription, metadata)
    assert rapport["empreintes_documentaires_dupliquees"] == [premiere["document"]["sha256"]]
    assert rapport["documents_recus"] == 3


def test_limite_totale_avant_ecriture(tmp_path, monkeypatch):
    from unocr.customs_reference import legal_importer
    transcription, metadata = fichiers_code(tmp_path)
    monkeypatch.setattr(legal_importer, "MAX_TOTAL", 1)
    with pytest.raises(ValueError, match="volumineux"):
        preparer_code(transcription, metadata, tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("cible", ["transcription", "metadata"])
def test_json_duplique_refuse(tmp_path, cible):
    transcription, metadata = fichiers_code(tmp_path)
    path = transcription if cible == "transcription" else metadata
    path.write_text('{"articles": [], "articles": [], "relations": []}')
    with pytest.raises(ValueError, match="dupliquée"):
        preparer_code(transcription, metadata)


def test_cli_plan_write_conditions_et_refus(tmp_path, capsys):
    transcription, metadata = fichiers_code(tmp_path)
    args = ["customs-code-prepare", str(transcription), "--metadata", str(metadata)]
    sortie = tmp_path / "lot"
    assert main([*args, "--out", str(sortie)]) == 0
    assert json.loads(capsys.readouterr().out)["ecrit"] is False
    assert not sortie.exists()
    assert main([*args, "--write"]) == 2
    assert "--out" in capsys.readouterr().err
    assert main([*args, "--write", "--out", str(sortie)]) == 0
    assert json.loads(capsys.readouterr().out)["ecrit"] is True
    assert main([*args, "--write", "--out", str(sortie)]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"


def test_cli_processus_independant_sans_stores(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
           "PYTHONDONTWRITEBYTECODE": "1", "UNOCR_DATA_DIR": str(tmp_path / "stores_absents"),
           "UNOCR_LOG_DIR": str(tmp_path / "logs_absents")}
    avant = snapshot(tmp_path)
    resultat = subprocess.run([sys.executable, "-m", "unocr.cli", "customs-code-prepare", str(transcription),
                               "--metadata", str(metadata)], env=env, cwd=tmp_path,
                              capture_output=True, text=True, timeout=30)
    assert resultat.returncode == 0, resultat.stderr
    assert json.loads(resultat.stdout)["articles_declares"] == 3
    assert snapshot(tmp_path) == avant


def test_schemas_generes_identiques():
    root = Path(__file__).resolve().parents[1] / "docs/customs/schemas"
    for modele in (CodeDocumentaireBatch, MetadataCode):
        assert json.loads((root / (modele.__name__ + ".schema.json")).read_text()) == modele.model_json_schema()


@pytest.mark.parametrize("valeur", [True, 0, "false"])
def test_publication_interdite_meme_types_ambigus(tmp_path, valeur):
    transcription, metadata = fichiers_code(tmp_path)
    brut = json.loads(transcription.read_text())
    brut["documents"] = [d["document"] for d in json.loads(metadata.read_text())["documents"]]
    brut["publication_active"] = valeur
    with pytest.raises(ValueError):
        CodeDocumentaireBatch.model_validate_json(json.dumps(brut))


@pytest.mark.parametrize("champ", ["documents", "publication_active", "validation_juridique"])
def test_enveloppe_transcription_ne_peut_pas_remplacer_metadata(tmp_path, champ):
    transcription, metadata = fichiers_code(tmp_path)
    modifier(transcription, lambda brut: brut.update({champ: True}))
    with pytest.raises(ValueError, match="Transcription JSON attendue"):
        preparer_code(transcription, metadata)


@pytest.mark.parametrize("cible", ["transcription", "metadata"])
def test_entree_symbolique_refusee(tmp_path, cible):
    transcription, metadata = fichiers_code(tmp_path)
    path = transcription if cible == "transcription" else metadata
    copie = tmp_path / "copie.json"
    copie.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(copie)
    with pytest.raises(ValueError, match="symbolique"):
        preparer_code(transcription, metadata)


def test_interruption_avant_manifest_conserve_quarantaine_partielle(tmp_path, monkeypatch):
    transcription, metadata = fichiers_code(tmp_path)
    sortie = tmp_path / "lot"
    ouvrir = Path.open
    def interrompre(path, *args, **kwargs):
        if path == sortie / "manifest.json":
            raise OSError("interruption de test avant manifeste final")
        return ouvrir(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", interrompre)
        with pytest.raises(OSError, match="interruption de test"):
            preparer_code(transcription, metadata, sortie)
    assert not (sortie / "manifest.json").exists()
    assert json.loads((sortie / "lot_code.json").read_text())["publication_active"] is False
    avant = snapshot(tmp_path)
    with pytest.raises(FileExistsError):
        preparer_code(transcription, metadata, sortie)
    assert snapshot(tmp_path) == avant


def test_octets_pdf_non_utf8_et_texte_non_normalise_preserves(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    meta = json.loads(metadata.read_text())
    doc = meta["documents"][0]
    pdf = tmp_path / doc["fichier_recu"]
    pdf.write_bytes(pdf.read_bytes() + b"\xff\x00")
    doc["document"]["sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    texte = "  FIXTURE NON OFFICIELLE\r\n  espaces conservés  "
    modifier(transcription, lambda brut: brut["articles"][0].update(texte_integral=texte, texte_origine=texte))
    sortie = tmp_path / "lot"
    preparer_code(transcription, metadata, sortie)
    assert (sortie / "document_0001.pdf").read_bytes() == pdf.read_bytes()
    assert json.loads((sortie / "lot_code.json").read_text())["articles"][0]["texte_integral"] == texte
