"""Archives de fixtures NON OFFICIELLES uniquement, aucune nomenclature nationale."""
import hashlib
import io
import json
import stat
import struct
import warnings
import zipfile

import pytest

from tests import test_customs_review
from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_review import ADMIN, BASE
from tests.test_customs_xlsx import xlsx_fichiers
from tests.test_customs_xml import xml_fichiers
from unocr.cli import main
from unocr.customs_reference.comparison import charger_lot
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.zip_source import ZIPRefuse, lire_zip

revue = test_customs_review.revue


def archive(membres, compression=zipfile.ZIP_DEFLATED):
    sortie = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(sortie, "w", compression) as z:
            for nom, contenu in membres:
                z.writestr(nom, contenu)
    return sortie.getvalue()


def zip_fichiers(tmp_path, format_contenu="csv"):
    if format_contenu == "xml":
        source, metadata = xml_fichiers(tmp_path)
    elif format_contenu == "xlsx":
        source, metadata = xlsx_fichiers(tmp_path)
    else:
        source, metadata = fichiers(tmp_path, csv=format_contenu == "csv")
    membre = "nomenclature/fixture_NON_OFFICIELLE." + format_contenu
    contenu_source = source.read_bytes()
    zip_path = tmp_path / "fixture_NON_OFFICIELLE.zip"
    zip_path.write_bytes(archive([(membre, contenu_source), ("notes_NON_OFFICIELLES.txt", b"NON OFFICIEL, pas un tarif national")]))
    meta = json.loads(metadata.read_text())
    meta.update(membre_zip=membre, format_contenu=format_contenu)
    meta["lot"]["source"].update(format="zip", sha256=hashlib.sha256(zip_path.read_bytes()).hexdigest())
    metadata.write_text(json.dumps(meta))
    return zip_path, metadata


@pytest.mark.parametrize("format_contenu", ["csv", "json", "xlsx", "xml"])
def test_plan_archive_et_rejeu_quatre_formats(tmp_path, format_contenu):
    source, metadata = zip_fichiers(tmp_path, format_contenu)
    avant = snapshot(tmp_path)
    rapport = preparer_tarif(source, metadata)
    assert snapshot(tmp_path) == avant
    assert rapport["lignes_importables"] == 1
    assert rapport["perimetre_lecture"]["format"] == "zip"
    assert rapport["perimetre_lecture"]["format_contenu"] == format_contenu
    with zipfile.ZipFile(source) as z:
        membre = rapport["perimetre_lecture"]["membre_zip"]
        assert rapport["perimetre_lecture"]["sha256_membre_lu"] == hashlib.sha256(z.read(membre)).hexdigest()
    assert rapport["perimetre_lecture"]["membres_non_importes"] == ["notes_NON_OFFICIELLES.txt"]
    sortie = tmp_path / "lot"
    preparer_tarif(source, metadata, sortie)
    assert (sortie / "source_recue.zip").read_bytes() == source.read_bytes()
    assert not (sortie / "nomenclature").exists()
    lot, relu = charger_lot(sortie)
    assert lot.source.format == "zip"
    assert lot.source.sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert lot.lignes[0].code_tarifaire_10 == "0101000000"
    assert lot.lignes[0].taux_tva is None
    if format_contenu != "json":
        assert lot.lignes[0].reference.localisateur.startswith("ZIP, membre nomenclature/")
    assert relu["perimetre_lecture"] == rapport["perimetre_lecture"]
    avant = snapshot(tmp_path)
    with pytest.raises(FileExistsError):
        preparer_tarif(source, metadata, sortie)
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("nom", ["../dangereux", "/absolu", "a/../b", "a/./b", "a//b", "a\\b", "C:source", "a\nb", "a\x00b"])
def test_membre_dangereux_meme_non_selectionne(nom):
    # ZipInfo tronque lui-même un NUL à l'écriture : injecter le défaut dans
    # les deux en-têtes binaires, sans changer leurs longueurs.
    contenu = archive([("source.csv", b"SOURCE NON OFFICIELLE"), (nom.replace("\x00", "Z"), b"REFUSER")])
    if "\x00" in nom:
        contenu = contenu.replace(b"aZb", b"a\x00b")
    with pytest.raises(ZIPRefuse):
        lire_zip(contenu, {"membre_zip": "source.csv", "format_contenu": "csv"})


@pytest.mark.parametrize("options", [{}, {"membre_zip": "absent", "format_contenu": "csv"},
    {"membre_zip": "source.csv", "format_contenu": "zip"}, {"membre_zip": "source.csv", "format_contenu": "xlsb"},
    {"membre_zip": "source.csv", "format_contenu": "pdf"}, {"membre_zip": "source.csv", "format_contenu": None},
    {"membre_zip": "../source.csv", "format_contenu": "csv"}, {"membre_zip": True, "format_contenu": "csv"}])
def test_selection_explicitement_requise(options):
    with pytest.raises(ZIPRefuse):
        lire_zip(archive([("source.csv", b"NON OFFICIEL")]), options)


@pytest.mark.parametrize("defaut", ["doublon", "symlink", "fifo", "dossier_ambigu", "source_vide", "membre_dossier", "compression", "tronque", "non_zip", "prefixe", "concatene", "chiffre", "crc"])
def test_archives_ambigues_ou_corrompues_refusees(defaut):
    membres = [("source.csv", b"NON OFFICIEL")]
    if defaut == "doublon":
        membres *= 2
    elif defaut in {"symlink", "fifo", "dossier_ambigu"}:
        info = zipfile.ZipInfo("extra")
        info.create_system = 3
        info.external_attr = {"symlink": stat.S_IFLNK, "fifo": stat.S_IFIFO, "dossier_ambigu": stat.S_IFDIR}[defaut] << 16
        membres.append((info, b"NON OFFICIEL"))
    elif defaut == "source_vide":
        membres = [("source.csv", b"")]
    elif defaut == "membre_dossier":
        membres = [("source.csv/", b"")]
    contenu = archive(membres, zipfile.ZIP_BZIP2 if defaut == "compression" else zipfile.ZIP_STORED)
    if defaut == "tronque":
        contenu = contenu[:20]
    elif defaut == "non_zip":
        contenu = b"PAS UN ZIP"
    elif defaut == "prefixe":
        contenu = b"EXE" + contenu
    elif defaut == "concatene":
        contenu += archive([("source.csv", b"AUTRE NON OFFICIEL")])
    elif defaut == "chiffre":
        b = bytearray(contenu)
        struct.pack_into("<H", b, 6, 1)
        central = b.index(b"PK\x01\x02")
        struct.pack_into("<H", b, central + 8, 1)
        contenu = bytes(b)
    elif defaut == "crc":
        contenu = contenu.replace(b"NON OFFICIEL", b"NON OFFICIEX", 1)
    with pytest.raises(ZIPRefuse):
        lire_zip(contenu, {"membre_zip": "source.csv", "format_contenu": "csv"})


@pytest.mark.parametrize("borne,valeur", [("MAX_ARCHIVE", 10), ("MAX_MEMBRES", 0), ("MAX_MEMBRE", 1), ("MAX_TOTAL", 1), ("MAX_RATIO", 1)])
def test_limites_avant_import(tmp_path, monkeypatch, borne, valeur):
    from unocr.customs_reference import zip_source
    source, metadata = zip_fichiers(tmp_path)
    monkeypatch.setattr(zip_source, borne, valeur)
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert snapshot(tmp_path) == avant


def test_crc_non_selectionne_pas_annonce_valide():
    contenu = archive([("source.csv", b"NON OFFICIEL"), ("notes", b"CRC NON VERIFIE")], zipfile.ZIP_STORED)
    contenu = contenu.replace(b"CRC NON VERIFIE", b"CRC NON VERIFIX", 1)
    _, perimetre = lire_zip(contenu, {"membre_zip": "source.csv", "format_contenu": "csv"})
    assert perimetre["controle_autres_membres"] == "metadonnees_zip_seulement_pas_crc_ni_contenu"


@pytest.mark.parametrize("champ,valeur", [("delimiteur", ";"), ("feuille", "TEST"), ("racine_xml", "TEST")])
def test_options_incompatibles_format_membre(tmp_path, champ, valeur):
    source, metadata = zip_fichiers(tmp_path, "json")
    meta = json.loads(metadata.read_text())
    meta[champ] = valeur
    metadata.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata)


def test_options_zip_interdites_hors_zip(tmp_path):
    source, metadata = fichiers(tmp_path, csv=True)
    meta = json.loads(metadata.read_text())
    meta.update(membre_zip="source.csv", format_contenu="csv")
    metadata.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="Options ZIP"):
        preparer_tarif(source, metadata)


def test_cli_plan_et_code_non_reconstitue(tmp_path, capsys):
    source, metadata = zip_fichiers(tmp_path)
    avant = snapshot(tmp_path)
    assert main(["customs-prepare", str(source), "--metadata", str(metadata)]) == 0
    assert json.loads(capsys.readouterr().out)["ecrit"] is False
    assert snapshot(tmp_path) == avant
    with zipfile.ZipFile(source) as z:
        membres = [(i.filename, z.read(i)) for i in z.infolist()]
    source.write_bytes(archive([(nom, contenu.replace(b"0101000000", b"101000000")) for nom, contenu in membres]))
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    avant = snapshot(tmp_path)
    assert main(["customs-prepare", str(source), "--metadata", str(metadata), "--out", str(tmp_path / "sortie"), "--write"]) == 2
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("suffixe", ["check", "search?q=010100", "tariff/0101000000", "tree?level=sections", "coverage"])
def test_archive_zip_via_api_protegee(revue, suffixe):
    client, racine, registre, cfg = revue
    entrees = cfg.root / "zip_entrees"
    entrees.mkdir()
    source, metadata = zip_fichiers(entrees)
    lot = racine / "tarif_zip"
    preparer_tarif(source, metadata, lot)
    contenu = json.loads(registre.read_text())
    empreinte = hashlib.sha256((lot / "manifest.json").read_bytes()).hexdigest()
    contenu["lots"].append({"id": "tarif_zip", "dossier": "tarif_zip", "type_lot": "tarif", "manifest_sha256": empreinte})
    registre.write_text(json.dumps(contenu))
    avant = snapshot(racine)
    reponse = client.get(BASE + "/lots/tarif_zip/" + suffixe, headers=ADMIN)
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["resultat"]["archive"]["manifest_sha256"] == empreinte
    assert reponse.json()["publication_active"] is False
    assert snapshot(racine) == avant


@pytest.mark.parametrize("format_contenu", ["csv", "json", "xlsx", "xml"])
def test_contenu_membre_invalide_refuse_sans_sortie(tmp_path, format_contenu):
    source, metadata = zip_fichiers(tmp_path, format_contenu)
    meta = json.loads(metadata.read_text())
    source.write_bytes(archive([(meta["membre_zip"], b"CONTENU INVALIDE NON OFFICIEL")]))
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert snapshot(tmp_path) == avant


def test_normalise_altere_rehache_refuse_au_rejeu(tmp_path):
    source, metadata = zip_fichiers(tmp_path)
    sortie = tmp_path / "lot"
    preparer_tarif(source, metadata, sortie)
    chemin = sortie / "lot.json"
    lot = json.loads(chemin.read_text())
    lot["lignes"][0]["designation_officielle_fr"] = "ALTÉRATION NON OFFICIELLE"
    chemin.write_text(json.dumps(lot))
    manifeste = json.loads((sortie / "manifest.json").read_text())
    manifeste["fichiers_sha256"]["lot.json"] = hashlib.sha256(chemin.read_bytes()).hexdigest()
    (sortie / "manifest.json").write_text(json.dumps(manifeste))
    avant = snapshot(sortie)
    with pytest.raises(ValueError, match="non reproductible"):
        charger_lot(sortie)
    assert snapshot(sortie) == avant
