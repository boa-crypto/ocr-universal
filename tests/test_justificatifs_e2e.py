"""Interface pièces → multipart réel → redémarrage → téléchargement/suppression."""
import hashlib

from tests._api_isolee import ApiIsolee

CONTENU = "Pièce E2E réelle\n".encode()


def test_justificatifs_navigateur_et_redemarrages(tmp_path):
    with ApiIsolee(tmp_path) as serveur:
        dossier = serveur.requete("/api/dossiers", {"label": "Pièces E2E isolées"})
        frais = serveur.requete("/api/frais", {"dossier_id": dossier["id"], "montant": 42})
        serveur.navigateur("ui_justificatifs_e2e.js", "ajouter", frais["id"])
        serveur.redemarrer()
        pieces = serveur.requete(f"/api/frais/{frais['id']}/justificatifs")
        assert len(pieces) == 1
        piece = pieces[0]
        assert piece["nom_fichier"] == "piece-e2e.txt"
        assert piece["taille_octets"] == len(CONTENU)
        assert piece["hash_sha256"] == hashlib.sha256(CONTENU).hexdigest()
        assert serveur.requete(f"/api/frais/{frais['id']}")["justificatifs"] == [piece["id"]]
        assert len(list((tmp_path / "data/justificatifs").glob("*.bin"))) == 1
        serveur.navigateur("ui_justificatifs_e2e.js", "supprimer", frais["id"])
        serveur.redemarrer()
        assert serveur.requete(f"/api/frais/{frais['id']}/justificatifs") == []
        assert serveur.requete(f"/api/frais/{frais['id']}")["justificatifs"] == []
        assert list((tmp_path / "data/justificatifs").iterdir()) == []
