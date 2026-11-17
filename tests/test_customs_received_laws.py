"""Copies utilisateur synthétiques : jamais affirmation d'authenticité officielle."""
import hashlib
import json

import pytest
from pydantic import ValidationError
from test_customs_legal import fichiers_code

from unocr.customs_reference.legal_comparison import charger_lot_code
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.legal_models import (
    DocumentJuridique,
    DocumentJuridiqueRecu,
    MetadataCode,
)
from unocr.customs_reference.source_catalog import inventorier_sources


def recu():
    return {"id":"RECU_TEST", "titre":"Copie NON OFFICIELLE", "organisme":"Non authentifié",
            "version_source":"Copie utilisateur non vérifiée", "sha256":"0"*64,"format":"pdf",
            "nature_document":"compilation","provenance":"piece_jointe_utilisateur",
            "nom_fichier_recu":"copie.txt.pdf","url":None}


def test_provenance_explicite_sans_url_officielle_inventee():
    d = DocumentJuridiqueRecu.model_validate(recu())
    assert d.url is None and d.verification == "non_verifiee"
    assert d.nature_document == "compilation" and d.date_publication is None
    with pytest.raises(ValidationError):
        DocumentJuridique.model_validate(recu())


@pytest.mark.parametrize("champ,valeur",[("url","https://evil.invalid/test.pdf"),
    ("verification","validee"),("provenance","officielle"),("nom_fichier_recu","../x.pdf"),
    ("nom_fichier_recu","C:x.pdf"),("titre"," "),("id","x\u0085y"),("titre","x\ud800y")])
def test_metadonnees_recues_invalides(champ,valeur):
    d=recu()
    d[champ]=valeur
    with pytest.raises(ValidationError):
        DocumentJuridiqueRecu.model_validate(d)


def test_aucun_repli_automatique_si_url_ou_provenance_absente():
    d=recu()
    d.pop("provenance")
    with pytest.raises(ValidationError):
        MetadataCode.model_validate({"documents":[{"fichier_recu":"x.pdf","document":d}]})


def test_import_rejeu_et_catalogue_sans_articles_fabriques(tmp_path):
    original=tmp_path/"copie.pdf"
    original.write_bytes(b"%PDF-1.7\nFIXTURE NON OFFICIELLE\n%%EOF")
    d=recu()
    d["sha256"]=hashlib.sha256(original.read_bytes()).hexdigest()
    d["nom_fichier_recu"]=original.name
    metadata=tmp_path/"metadata.json"
    metadata.write_text(json.dumps({"documents":[{"fichier_recu":original.name,"document":d}]}))
    transcription=tmp_path/"transcription.json"
    transcription.write_text('{"articles":[],"relations":[]}')
    sortie=tmp_path/"archive"
    rapport=preparer_code(transcription,metadata,sortie)
    lot,rejeu=charger_lot_code(sortie)
    assert not lot.articles and not lot.relations and lot.documents[0].url is None
    assert (sortie/"document_0001.pdf").read_bytes() == original.read_bytes()
    assert rapport["documents_sans_article_transcrit"] == [d["id"]]
    assert rejeu["publication_active"] is False
    catalogue=inventorier_sources(sortie,"code")
    assert catalogue["resultats"][0]["source_declaree"]["provenance"] == "piece_jointe_utilisateur"
    assert catalogue["authenticite_etablie"] is False


def test_ancien_mode_reste_identique_et_url_non_officielle_refusee(tmp_path):
    trans,metadata=fichiers_code(tmp_path)
    original=json.loads(metadata.read_text())
    sortie=tmp_path/"legacy"
    preparer_code(trans,metadata,sortie)
    lot,_=charger_lot_code(sortie)
    assert all(isinstance(d,DocumentJuridique) for d in lot.documents)
    assert "provenance" not in lot.documents[0].model_dump()
    original["documents"][0]["document"]["url"]="https://evil.invalid/doc.pdf"
    with pytest.raises(ValidationError):
        MetadataCode.model_validate(original)
