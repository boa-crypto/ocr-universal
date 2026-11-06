"""XML de fixtures techniques NON OFFICIELLES ; aucun fichier national simulé."""
import hashlib
import json
from types import SimpleNamespace
from xml.sax.saxutils import escape

import pytest

from tests import test_customs_review
from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr import backup
from unocr.cli import main
from unocr.customs_reference.comparison import charger_lot, comparer_lots
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.xml_table import XMLRefuse, lire_xml

revue = test_customs_review.revue


def xml_fichiers(tmp_path):
    csv, metadata = fichiers(tmp_path, csv=True)
    headers, valeurs = [ligne.split(";") for ligne in csv.read_text().splitlines()]
    contenu = '<?xml version="1.0" encoding="UTF-8"?>\n<Tarif>\n  <Ligne>\n'
    for cle, valeur in zip(headers, valeurs):
        contenu += f"    <{cle}>{escape(valeur)}</{cle}>\n"
    contenu += "  </Ligne>\n</Tarif>"
    source = tmp_path / "fixture_NON_OFFICIELLE.xml"
    source.write_bytes(contenu.encode("utf-8"))
    meta = json.loads(metadata.read_text())
    meta.update(racine_xml="Tarif", ligne_xml="Ligne")
    meta["lot"]["source"].update(format="xml", sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    metadata.write_text(json.dumps(meta))
    return source, metadata


def actualiser(source, metadata, contenu):
    source.write_bytes(contenu if isinstance(contenu, bytes) else contenu.encode("utf-8"))
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))


def test_plan_archive_rejeu_et_diff_sans_migration(tmp_path):
    source, metadata = xml_fichiers(tmp_path)
    avant = snapshot(tmp_path)
    rapport = preparer_tarif(source, metadata)
    assert snapshot(tmp_path) == avant
    assert rapport["lignes_source_lues"] == rapport["codes_uniques"] == 1
    assert rapport["perimetre_lecture"]["racine_xml"] == "Tarif"
    assert rapport["perimetre_lecture"]["encodage"] == "UTF-8"
    assert rapport["completude_reglementaire"] == "non_etablie"
    sortie = tmp_path / "lot"
    preparer_tarif(source, metadata, sortie)
    assert (sortie / "source_recue.xml").read_bytes() == source.read_bytes()
    lot, releve = charger_lot(sortie)
    ligne = lot.lignes[0]
    assert ligne.code_tarifaire_10 == "0101000000"
    assert ligne.chapitre == "01"
    assert ligne.taux_tva is None
    assert ligne.reference.localisateur == "XML, élément Ligne, ligne physique 3"
    assert releve["perimetre_lecture"] == rapport["perimetre_lecture"]
    assert comparer_lots(sortie, sortie)["lignes"]["modifies"] == []
    avant = snapshot(tmp_path)
    with pytest.raises(FileExistsError):
        preparer_tarif(source, metadata, sortie)
    assert snapshot(tmp_path) == avant


def test_arabe_entites_cdata_ordre_champs_et_non_importees():
    contenu = ('<Tarif><Ligne><Code>0101000000</Code><Texte>نص غير رسمي &amp; test</Texte><Ignore>NE PAS IMPORTER</Ignore></Ligne>'
               '<Ligne><Ignore/><Texte><![CDATA[<NON OFFICIEL>]]></Texte><Code>0101000001</Code></Ligne></Tarif>').encode()
    rows, perimetre = lire_xml(contenu, {"racine_xml": "Tarif", "ligne_xml": "Ligne"})
    assert rows[0][1]["Texte"] == "نص غير رسمي & test"
    assert rows[1][1]["Texte"] == "<NON OFFICIEL>"
    assert rows[1][1]["Ignore"] == ""
    assert perimetre["headers"] == ["Code", "Texte", "Ignore"]


@pytest.mark.parametrize("contenu", [
    b"", b"\xff", b"<Tarif>", b"<Autre/>", b"<Tarif/>", b"<Tarif><Ligne/></Tarif>",
    b"<Tarif><Autre/></Tarif>", b"<Tarif>texte<Ligne><A>1</A></Ligne></Tarif>",
    b"<Tarif><Ligne>texte<A>1</A></Ligne></Tarif>",
    b"<Tarif><Ligne><A><B>1</B></A></Ligne></Tarif>",
    b"<Tarif><Ligne><A>1</A><A>2</A></Ligne></Tarif>",
    b"<Tarif><Ligne><A>1</A></Ligne><Ligne><B>1</B></Ligne></Tarif>",
    b'<Tarif x="1"><Ligne><A>1</A></Ligne></Tarif>',
    b'<Tarif><Ligne x="1"><A>1</A></Ligne></Tarif>',
    b'<Tarif><Ligne><A x="1">1</A></Ligne></Tarif>',
    b'<Tarif xmlns="urn:non-officiel"><Ligne><A>1</A></Ligne></Tarif>',
    b'<Tarif><Ligne><n:A xmlns:n="urn:non-officiel">1</n:A></Ligne></Tarif>',
    b'<?xml version="1.1"?><Tarif><Ligne><A>1</A></Ligne></Tarif>',
    b'<?xml version="1.0" encoding="ISO-8859-1"?><Tarif><Ligne><A>1</A></Ligne></Tarif>',
    b'<Tarif><!-- NON OFFICIEL --><Ligne><A>1</A></Ligne></Tarif>',
    b'<?xml-stylesheet href="https://example.invalid/test"?><Tarif><Ligne><A>1</A></Ligne></Tarif>',
    b'<!DOCTYPE Tarif><Tarif><Ligne><A>1</A></Ligne></Tarif>',
    b'<!DOCTYPE Tarif SYSTEM "file:///NE_PAS_LIRE"><Tarif><Ligne><A>1</A></Ligne></Tarif>',
    b'<!DOCTYPE Tarif [<!ENTITY x "NON OFFICIEL">]><Tarif><Ligne><A>&x;</A></Ligne></Tarif>',
    b'<!DOCTYPE Tarif [<!ENTITY x SYSTEM "https://example.invalid/test">]><Tarif><Ligne><A>&x;</A></Ligne></Tarif>',
    b'<Tarif><Ligne><A>&inconnue;</A></Ligne></Tarif>',
    b'<Tarif><Ligne><A>&#0;</A></Ligne></Tarif>',
    '<Tarif><Ligne><A>NON OFFICIEL</A></Ligne></Tarif>'.encode('utf-16'),
])
def test_xml_hors_contrat_refuse(contenu):
    with pytest.raises(XMLRefuse):
        lire_xml(contenu, {"racine_xml": "Tarif", "ligne_xml": "Ligne"})


@pytest.mark.parametrize("champ,valeur", [("racine_xml", None), ("racine_xml", "/Tarif"), ("racine_xml", "Tarif/Ligne"),
    ("ligne_xml", "*"), ("ligne_xml", "n:Ligne"), ("ligne_xml", True), ("ligne_xml", ""),
    ("delimiteur", ";"), ("feuille", "Tarif"), ("ligne_entete", 1)])
def test_options_xml_strictes(tmp_path, champ, valeur):
    source, metadata = xml_fichiers(tmp_path)
    meta = json.loads(metadata.read_text())
    meta[champ] = valeur
    metadata.write_text(json.dumps(meta))
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("champ,ancien,nouveau", [
    ("code", "0101000000", "101000000"), ("code", "0101000000", "٠١٠١٠٠٠٠٠٠"),
    ("code", "0101000000", " 0101000000"), ("parent", "<Chap>01</Chap>", "<Chap>02</Chap>"),
    ("texte", "FIXTURE NON OFFICIELLE", "   "),
])
def test_validation_metier_reutilisee(tmp_path, champ, ancien, nouveau):
    source, metadata = xml_fichiers(tmp_path)
    actualiser(source, metadata, source.read_text().replace(ancien, nouveau))
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("borne,valeur", [("MAX_XML", 10), ("MAX_LIGNES", 0), ("MAX_COLONNES", 0),
    ("MAX_CELLULES", 0), ("MAX_TEXTE_CHAMP", 1)])
def test_bornes_sans_import_partiel(tmp_path, monkeypatch, borne, valeur):
    from unocr.customs_reference import xml_table
    source, metadata = xml_fichiers(tmp_path)
    monkeypatch.setattr(xml_table, borne, valeur)
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert snapshot(tmp_path) == avant


def test_doublon_codes_et_hash_incorrect_refuses(tmp_path):
    source, metadata = xml_fichiers(tmp_path)
    contenu = source.read_text()
    ligne = contenu[contenu.index("  <Ligne>"):contenu.index("  </Ligne>") + len("  </Ligne>")]
    actualiser(source, metadata, contenu.replace("</Tarif>", ligne + "</Tarif>"))
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata)
    source.write_bytes(source.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Empreinte"):
        preparer_tarif(source, metadata)


def test_cli_xml_sans_ecriture_et_refus(tmp_path, capsys):
    source, metadata = xml_fichiers(tmp_path)
    avant = snapshot(tmp_path)
    assert main(["customs-prepare", str(source), "--metadata", str(metadata)]) == 0
    assert json.loads(capsys.readouterr().out)["ecrit"] is False
    assert snapshot(tmp_path) == avant
    actualiser(source, metadata, b"<INVALIDE>")
    assert main(["customs-prepare", str(source), "--metadata", str(metadata)]) == 2


def test_options_xml_interdites_sur_autre_format(tmp_path):
    source, metadata = fichiers(tmp_path, csv=True)
    meta = json.loads(metadata.read_text())
    meta.update(racine_xml="Tarif", ligne_xml="Ligne")
    metadata.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="Options XML"):
        preparer_tarif(source, metadata)


def test_colonnes_non_importees_et_texte_litteral(tmp_path):
    source, metadata = xml_fichiers(tmp_path)
    contenu = source.read_text().replace("FIXTURE NON OFFICIELLE", "نص غير رسمي &amp; TEST").replace("</Ligne>", "<Notes>NON IMPORTÉ</Notes></Ligne>")
    actualiser(source, metadata, contenu)
    sortie = tmp_path / "lot"
    rapport = preparer_tarif(source, metadata, sortie)
    assert rapport["colonnes_non_importees"] == ["Notes"]
    lot, _ = charger_lot(sortie)
    assert lot.lignes[0].designation_officielle_fr == "نص غير رسمي & TEST"


@pytest.mark.parametrize("suffixe", ["check", "search?q=010100", "tree?level=sections", "tariff/0101000000", "coverage"])
def test_xml_via_api_protegee_et_epinglee(revue, suffixe):
    client, racine, registre, cfg = revue
    entrees = cfg.root / "xml_entrees"
    entrees.mkdir()
    source, metadata = xml_fichiers(entrees)
    lot = racine / "tarif_xml"
    preparer_tarif(source, metadata, lot)
    contenu = json.loads(registre.read_text())
    empreinte = hashlib.sha256((lot / "manifest.json").read_bytes()).hexdigest()
    contenu["lots"].append({"id": "tarif_xml", "dossier": "tarif_xml", "type_lot": "tarif", "manifest_sha256": empreinte})
    registre.write_text(json.dumps(contenu))
    avant = snapshot(racine)
    reponse = client.get(BASE + "/lots/tarif_xml/" + suffixe, headers=ADMIN)
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["publication_active"] is False
    assert reponse.json()["resultat"]["archive"]["manifest_sha256"] == empreinte
    assert snapshot(racine) == avant


def test_sauvegarde_reprise_xml_dans_magasin_neuf(tmp_cfg):
    entrees = tmp_cfg.root / "xml_entrees"
    entrees.mkdir()
    source, metadata = xml_fichiers(entrees)
    racine = tmp_cfg.data_dir / "customs-quarantine"
    racine.mkdir()
    preparer_tarif(source, metadata, racine / "tarif_xml")
    avant = snapshot(racine)
    sauvegarde = backup.creer_sauvegarde(tmp_cfg, inclure_quarantaine=True)
    cible = SimpleNamespace(data_dir=tmp_cfg.root / "reprise" / "data", log_dir=tmp_cfg.root / "reprise" / "logs")
    backup.restaurer_sauvegarde(cible, sauvegarde.chemin, inclure_quarantaine=True)
    restaure = cible.data_dir / "customs-quarantine" / "tarif_xml"
    lot, rapport = charger_lot(restaure)
    assert lot.source.format == "xml" and lot.statut == "quarantaine"
    assert rapport["publication_active"] is False
    assert (restaure / "source_recue.xml").read_bytes() == source.read_bytes()
    assert snapshot(racine) == avant


def test_lot_xml_rehache_mais_divergent_du_rejeu_refuse(tmp_path):
    source, metadata = xml_fichiers(tmp_path)
    sortie = tmp_path / "lot"
    preparer_tarif(source, metadata, sortie)
    lot_path = sortie / "lot.json"
    lot = json.loads(lot_path.read_text())
    lot["lignes"][0]["designation_officielle_fr"] = "ALTÉRATION NON OFFICIELLE"
    lot_path.write_text(json.dumps(lot))
    manifeste = json.loads((sortie / "manifest.json").read_text())
    manifeste["fichiers_sha256"]["lot.json"] = hashlib.sha256(lot_path.read_bytes()).hexdigest()
    (sortie / "manifest.json").write_text(json.dumps(manifeste))
    avant = snapshot(sortie)
    with pytest.raises(ValueError, match="non reproductible"):
        charger_lot(sortie)
    assert snapshot(sortie) == avant
