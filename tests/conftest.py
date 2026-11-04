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
def tmp_cfg(tmp_path):
    import copy

    from unocr import api
    from unocr.config import DEFAULTS, Config, get_config, set_config
    from unocr.storage import JobStore
    original = get_config()
    original_store = api.store
    original_cfg = api.cfg
    original_app_cfg = api.app.state.cfg
    data = copy.deepcopy(DEFAULTS)
    cfg = Config(data, tmp_path)
    set_config(cfg)
    # Isolation complète : sans réaffecter api.cfg, le journal d'audit serait
    # scindé entre la config réelle (lue par /api/audit) et la config isolée
    # (utilisée par le store) — les événements sembleraient disparaître.
    api.store = JobStore(cfg)
    api.cfg = cfg
    api.app.state.cfg = cfg
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
    set_config(original)
