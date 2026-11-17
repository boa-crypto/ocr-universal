"""CRUD navigateur contre une vraie API, trois démarrages et SQLite temporaire."""
from tests._api_isolee import ApiIsolee


def test_crud_declarations_navigateur_et_redemarrage(tmp_path):
    with ApiIsolee(tmp_path) as serveur:
        dossier = serveur.requete("/api/dossiers", {"label": "Dossier E2E isolé"})
        serveur.navigateur("ui_declarations_e2e.js", "creer-modifier", dossier["id"])
        serveur.redemarrer()
        assert (tmp_path / "data/metier.sqlite3").is_file()
        declarations = serveur.requete("/api/declarations")
        assert len(declarations) == 1
        declaration = declarations[0]
        assert declaration["numero_declaration"] == "DECL-E2E-MODIFIEE"
        assert declaration["statut"] == "deposee"
        assert declaration["date_depot"] == "2026-11-04"
        assert declaration["agent_declarant"] == "Agent E2E"
        serveur.navigateur("ui_declarations_e2e.js", "supprimer", dossier["id"])
        serveur.redemarrer()
        assert serveur.requete("/api/declarations") == []
