"""Verrous des correctifs d'audit (vague 4) : permissions du coffre de secrets
et avertissement de bind ouvert.

**Pourquoi ce fichier.** Ces deux points viennent de `docs/AUDIT.md` :
- A7 : `secrets.py` avalait l'échec du `chmod` — le coffre pouvait rester
  lisible par les autres utilisateurs, en silence. L'état est désormais
  exposé par `describe()`.
- B4 : l'API écoute par défaut sur `0.0.0.0` sans jeton. Le choix est assumé,
  mais il doit être *annoncé* au démarrage, pas découvert par accident.
"""
from __future__ import annotations

import io
import logging
import os
import stat
import tempfile
from pathlib import Path

from unocr.connectors.secrets import SecretStore

# ─────────────────────────── A7 · permissions du coffre ──────────────────────

def test_describe_expose_les_permissions_du_coffre() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = SecretStore(Path(d))
        store.set("demo", "api_key", "valeur-secrete")
        desc = store.describe()
        assert "vault_file_permissions" in desc, "permissions du coffre non exposées"
        assert "vault_file_secure" in desc, "état de sécurité non exposé"
        assert store.get("demo", "api_key") == "valeur-secrete"
        # sur un système de fichiers POSIX, l'écriture doit imposer 0600
        if os.name == "posix":
            assert desc["vault_file_permissions"] == "0o600"
            assert desc["vault_file_secure"] is True


def test_describe_sans_fichier_est_inconnu_pas_non_sur() -> None:
    """Aucun coffre encore écrit = état inconnu, pas « non sûr ».

    Un `false` ici serait lu comme « le coffre est lisible », ce qui est faux :
    il n'existe simplement pas encore.
    """
    with tempfile.TemporaryDirectory() as d:
        store = SecretStore(Path(d))
        desc = store.describe()
        assert desc["vault_file_permissions"] == "absent"
        assert desc["vault_file_secure"] is None


def test_describe_detecte_un_coffre_trop_permissif() -> None:
    """Si les permissions sont relâchées, `describe()` doit le dire."""
    with tempfile.TemporaryDirectory() as d:
        store = SecretStore(Path(d))
        store.set("demo", "api_key", "valeur-secrete")
        if os.name != "posix":
            return
        coffre = Path(d) / "secrets.enc"
        os.chmod(coffre, 0o644)          # situation à risque, volontaire
        desc = store.describe()
        assert desc["vault_file_permissions"] == "0o644"
        assert desc["vault_file_secure"] is False, (
            "un coffre lisible par les autres utilisateurs ne doit pas être "
            "déclaré sûr"
        )


def test_ecriture_reaffiche_les_permissions() -> None:
    """Une nouvelle écriture doit refermer les permissions, pas les laisser."""
    with tempfile.TemporaryDirectory() as d:
        store = SecretStore(Path(d))
        store.set("demo", "api_key", "valeur-secrete")
        if os.name != "posix":
            return
        coffre = Path(d) / "secrets.enc"
        os.chmod(coffre, 0o666)
        store.set("demo", "autre", "valeur-secrete-2")
        mode = stat.S_IMODE(coffre.stat().st_mode)
        assert mode == 0o600, f"permissions après réécriture : {oct(mode)}"


# ─────────────────────── B4 · avertissement de bind ouvert ───────────────────

def _avertissement_pour(hote: str) -> str:
    from unocr import api

    class FauxCfg:
        def get(self, cle, defaut=None):
            return {"api.host": hote}.get(cle, defaut)

    tampon = io.StringIO()
    handler = logging.StreamHandler(tampon)
    logger = logging.getLogger("unocr")
    ancien = api.cfg
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    try:
        api.cfg = FauxCfg()
        api._avertit_bind_ouvert()
    finally:
        api.cfg = ancien
        logger.removeHandler(handler)
    return tampon.getvalue()


def test_pas_davertissement_en_local() -> None:
    for hote in ("127.0.0.1", "localhost", "::1", ""):
        assert "SANS jeton" not in _avertissement_pour(hote), (
            f"avertissement abusif pour {hote!r}"
        )


def test_avertissement_si_expose_sans_jeton() -> None:
    for hote in ("0.0.0.0", "192.168.1.5"):
        message = _avertissement_pour(hote)
        assert "SANS jeton" in message, f"pas d'avertissement pour {hote!r}"
        assert "UNIOCR_TOKEN" in message, "l'avertissement doit donner la marche à suivre"


def test_pas_davertissement_avec_jeton_defini() -> None:
    from unocr import api

    ancien = api._AUTH_TOKEN
    try:
        api._AUTH_TOKEN = "un-jeton"
        assert "SANS jeton" not in _avertissement_pour("0.0.0.0"), (
            "inutile d'avertir quand un jeton protège déjà l'API"
        )
    finally:
        api._AUTH_TOKEN = ancien
