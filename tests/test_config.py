"""Tests de configuration : résolution des chemins et variables d'environnement."""
import copy
import os

from unocr.config import DEFAULTS, Config, set_config


def _cfg(root, **overrides):
    data = copy.deepcopy(DEFAULTS)
    data.update(overrides)
    return Config(data, root)


def test_data_dir_default_relative_to_root(tmp_path, monkeypatch):
    monkeypatch.delenv("UNOCR_DATA_DIR", raising=False)
    cfg = _cfg(tmp_path)
    assert cfg.data_dir == tmp_path / "data"
    assert cfg.data_dir.is_dir()


def test_log_dir_default_relative_to_root(tmp_path, monkeypatch):
    monkeypatch.delenv("UNOCR_LOG_DIR", raising=False)
    cfg = _cfg(tmp_path)
    assert cfg.log_dir == tmp_path / "logs"
    assert cfg.log_dir.is_dir()


def test_data_dir_env_override(tmp_path, monkeypatch):
    """UNOCR_DATA_DIR sort les données de la racine (volume Docker)."""
    cible = tmp_path / "volume"
    monkeypatch.setenv("UNOCR_DATA_DIR", str(cible))
    cfg = _cfg(tmp_path)
    assert cfg.data_dir == cible.resolve()
    assert cfg.data_dir.is_dir()


def test_log_dir_env_override(tmp_path, monkeypatch):
    cible = tmp_path / "logs-volume"
    monkeypatch.setenv("UNOCR_LOG_DIR", str(cible))
    cfg = _cfg(tmp_path)
    assert cfg.log_dir == cible.resolve()
    assert cfg.log_dir.is_dir()


def test_env_override_wins_over_config(tmp_path, monkeypatch):
    """La variable d'environnement prime sur jobs.data_dir du fichier de config."""
    monkeypatch.setenv("UNOCR_DATA_DIR", str(tmp_path / "env"))
    cfg = _cfg(tmp_path, jobs={"data_dir": "autre"})
    assert cfg.data_dir == (tmp_path / "env").resolve()


def test_web_dir_and_profiles_dir(tmp_path):
    cfg = _cfg(tmp_path)
    assert cfg.web_dir == tmp_path / "web"


def test_get_dotted_and_missing(tmp_path):
    cfg = _cfg(tmp_path, jobs={"data_dir": "d"})
    assert cfg.get("jobs.data_dir") == "d"
    assert cfg.get("jobs.inconnu", "repli") == "repli"
    assert cfg["jobs.data_dir"] == "d"


def test_set_config_roundtrip(tmp_path):
    original = os.environ.get("UNOCR_ROOT")
    try:
        cfg = _cfg(tmp_path)
        set_config(cfg)
        from unocr.config import get_config
        assert get_config() is cfg
    finally:
        if original is None:
            os.environ.pop("UNOCR_ROOT", None)
        else:
            os.environ["UNOCR_ROOT"] = original


def test_load_config_uses_unocr_root(tmp_path, monkeypatch):
    from unocr.config import load_config
    monkeypatch.setenv("UNOCR_ROOT", str(tmp_path))
    monkeypatch.delenv("UNOCR_DATA_DIR", raising=False)
    cfg = load_config()
    assert cfg.root == tmp_path.resolve()
    assert cfg.data_dir == tmp_path.resolve() / "data"
