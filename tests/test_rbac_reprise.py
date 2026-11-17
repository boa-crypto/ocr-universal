"""Le cloisonnement doit survivre à une sauvegarde puis une restauration.

**Pourquoi ce fichier existe.** `rbac.json` vit à la racine de `data/`, donc
en dehors des répertoires que le module de sauvegarde parcourt. Il n'était
sauvegardé ni restauré : après une reprise, le registre devenait inactif et
l'API repassait **ouverte à tous** — silencieusement. L'opérateur croirait ses
rôles toujours en place. Un cloisonnement perdu en silence est pire qu'un
cloisonnement jamais mis en place.

Ces tests verrouillent les deux moitiés du correctif : l'archive contient le
fichier, et le processus recharge le registre après restauration.
"""
import json
import shutil

import pytest

from unocr import api
from unocr.config import DEFAULTS, Config
from unocr.rbac import RegistreRBAC


@pytest.fixture()
def magasin(tmp_path, monkeypatch):
    # Ne pas hériter du magasin de l'hôte/du processus de test : la restauration
    # supprime ce répertoire. Le root Config seul ne prime pas sur ces variables.
    monkeypatch.setenv("UNOCR_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("UNOCR_LOG_DIR", str(tmp_path / "logs"))
    (tmp_path / "data" / "jobs").mkdir(parents=True)
    (tmp_path / "data" / "rbac.json").write_text(json.dumps({"utilisateurs": [
        {"nom": "marie", "jeton": "jeton-marie", "roles": ["operateur"],
         "dossiers": ["D1"]}]}, ensure_ascii=False), encoding="utf-8")
    return Config(DEFAULTS, tmp_path)


def test_rbac_json_est_dans_l_archive(magasin, tmp_path):
    from unocr import backup as B
    r = B.creer_sauvegarde(magasin, destination=tmp_path / "sauv")
    import zipfile
    noms = zipfile.ZipFile(r.chemin).namelist()
    assert any(n.endswith("rbac.json") for n in noms), noms


def test_cloisonnement_survit_a_une_reprise_complete(magasin, tmp_path):
    """Le scénario de catastrophe : le magasin est perdu, on restaure."""
    from unocr import backup as B
    r = B.creer_sauvegarde(magasin, destination=tmp_path / "sauv")
    shutil.rmtree(magasin.data_dir)
    B.restaurer_sauvegarde(magasin, r.chemin, force=True)

    assert (magasin.data_dir / "rbac.json").is_file()
    reg = RegistreRBAC.charger(magasin.data_dir)
    assert reg.actif is True, "le registre doit rester actif après reprise"
    u = reg.resoudre("jeton-marie")
    assert u is not None and u.voit_dossier("D1") and not u.voit_dossier("D2")


def test_sans_rbac_json_l_archive_reste_valide(magasin, tmp_path):
    """Absence de fichier de rôles = déploiement sans cloisonnement.

    La sauvegarde doit fonctionner quand même : un déploiement sans RBAC n'a
    aucune raison d'être empêché de sauvegarder.
    """
    from unocr import backup as B
    (magasin.data_dir / "rbac.json").unlink()
    r = B.creer_sauvegarde(magasin, destination=tmp_path / "sauv")
    assert r.chemin.is_file()
    B.restaurer_sauvegarde(magasin, r.chemin, force=True)
    assert RegistreRBAC.charger(magasin.data_dir).actif is False


def test_restauration_recharge_le_registre_du_processus(tmp_cfg, monkeypatch):
    """Le processus doit voir les droits restaurés, pas ceux d'avant.

    Sans rechargement, un utilisateur révoqué avant la sauvegarde
    continuerait d'accéder à ses dossiers après la restauration.
    """

    from fastapi.testclient import TestClient

    from unocr import backup as B

    # L'etat global est capture AVANT toute modification. Le capturer plus tard
    # restaurerait le registre temporaire, et le RBAC resterait actif pour tous
    # les tests suivants.
    original = api._rbac

    # un registre actif avec un utilisateur révoqué ensuite
    (tmp_cfg.data_dir / "jobs").mkdir(parents=True, exist_ok=True)
    (tmp_cfg.data_dir / "rbac.json").write_text(json.dumps({"utilisateurs": [
        {"nom": "marie", "jeton": "jeton-marie", "roles": ["operateur"],
         "dossiers": ["*"]}]}, ensure_ascii=False), encoding="utf-8")
    api._rbac = RegistreRBAC.charger(tmp_cfg.data_dir)
    import glob
    destination = tmp_cfg.data_dir.parent / "sauv"
    B.creer_sauvegarde(tmp_cfg, destination=destination)
    archive = sorted(glob.glob(str(destination / "*.zip")))[0]

    # on révoque marie dans le processus courant
    api._rbac.retirer("marie")
    assert api._rbac.resoudre("jeton-marie") is None

    # le RBAC est actif : la restauration exige un administrateur. On passe par
    # le jeton d'environnement, qui est le passe-partout documenté.
    monkeypatch.setattr(api, "_AUTH_TOKEN", "master-test")
    try:
        with TestClient(api.app) as c:
            r = c.post("/api/backups/restore",
                       json={"chemin": archive, "force": True},
                       headers={"Authorization": "Bearer master-test"})
            assert r.status_code == 200, r.text
        # après restauration, marie est de retour : le registre a été rechargé
        assert api._rbac.resoudre("jeton-marie") is not None
    finally:
        api._rbac = original
