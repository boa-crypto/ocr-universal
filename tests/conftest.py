"""Fixtures pytest communes."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from make_fixtures import FIXTURES, make_all


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    make_all()
    return FIXTURES


@pytest.fixture(scope="session")
def ground_truth(fixtures_dir) -> dict:
    import json
    return json.loads((fixtures_dir / "ground_truth.json").read_text(encoding="utf-8"))


@pytest.fixture()
def tmp_cfg(tmp_path, monkeypatch):
    import copy

    from unocr import api
    from unocr.config import DEFAULTS, Config, get_config, set_config
    from unocr.storage import JobStore
    original = get_config()
    original_store = api.store
    original_cfg = api.cfg
    original_app_cfg = api.app.state.cfg
    # Une variable UNOCR_DATA_DIR héritée du poste ne doit jamais court-circuiter
    # le tmp_path et partager les données entre tests (ou toucher le magasin réel).
    monkeypatch.setenv("UNOCR_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("UNOCR_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("UNOCR_USER_PROFILES_DIR", str(tmp_path / "user_profiles"))
    data = copy.deepcopy(DEFAULTS)
    cfg = Config(data, tmp_path)
    set_config(cfg)
    # Isolation complète : sans réaffecter api.cfg, le journal d'audit serait
    # scindé entre la config réelle (lue par /api/audit) et la config isolée
    # (utilisée par le store) — les événements sembleraient disparaître.
    api.store = JobStore(cfg)
    api.cfg = cfg
    api.app.state.cfg = cfg
    # Le store de dossiers est construit à l'import de `api` : sans ce
    # remplacement, les tests d'API écriraient dans `data/dossiers` réel.
    from unocr.dossier import DossierStore
    original_dossiers = api._dossiers
    api._dossiers = DossierStore(cfg.data_dir / "dossiers", log_dir=cfg.log_dir)
    # La limitation de débit est volontairement globale au processus (c'est sa
    # fonction côté serveur). Sans cette remise à zéro, les requêtes d'un test
    # s'ajouteraient à celles du précédent et les tests suivants recevraient
    # des 429 qui ne traduisent aucun abus réel.
    if hasattr(api, "_compteur"):
        api._compteur.evenements.clear()
    # Le registre de rôles est un état global du module `api`. Un test qui le
    # remplace sans le restaurer le laisse pointant vers un répertoire
    # temporaire supprimé : le RBAC reste actif, plus aucun jeton ne résout, et
    # **tous** les tests suivants reçoivent des 401 inexpliqués. Ce filet
    # attrape la classe entière de bugs d'isolation.
    original_rbac = getattr(api, "_rbac", None)
    yield cfg
    if original_rbac is not None:
        api._rbac = original_rbac
    api.store = original_store
    api.cfg = original_cfg
    api.app.state.cfg = original_app_cfg
    api._dossiers = original_dossiers
    set_config(original)


@pytest.fixture
def client_factory(tmp_path, monkeypatch):
    """API métier temporaire, sans état ni données du serveur du poste."""
    from types import SimpleNamespace

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from unocr.routes import declarations, expeditions, frais, terminal

    cfg = SimpleNamespace(data_dir=tmp_path, log_dir=tmp_path / "logs")
    monkeypatch.setattr(declarations, "cfg", cfg)
    monkeypatch.setattr(terminal, "cfg", cfg)
    monkeypatch.setattr(expeditions, "cfg", cfg)
    monkeypatch.setattr(frais, "cfg", cfg)
    # Dossiers réellement présents sur disque, pas des identifiants fictifs.
    import json
    (tmp_path / "dossiers").mkdir(exist_ok=True)
    for identifiant in ("dos_test", "dos_autre"):
        (tmp_path / "dossiers" / f"{identifiant}.json").write_text(
            json.dumps({"id": identifiant, "label": identifiant}), encoding="utf-8")

    def nouveau():
        app = FastAPI()
        app.include_router(declarations.router)
        app.include_router(terminal.router)
        app.include_router(expeditions.router)
        app.include_router(frais.router)
        return TestClient(app)
    return nouveau
