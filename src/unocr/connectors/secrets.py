"""Stockage sécurisé des secrets de connecteurs (phase 12).

**Règle absolue.** Un identifiant, un mot de passe, un jeton ou une clé d'API
n'est jamais écrit en clair — ni dans le code, ni dans les journaux, ni dans un
fichier de configuration lisible. Les secrets sont chiffrés en AES-256-GCM via
`crypto_store` et rangés dans `data/connectors/secrets.enc`, avec les
permissions les plus restrictives possibles.

Le fichier de clé (`data/connectors/secret.key`, 0600) est distinct du fichier
chiffré. S'il est perdu, les secrets sont définitivement illisibles — c'est
annoncé à la création.

Ce module ne fournit aucune capacité de contournement d'authentification : il
stocke ce que l'utilisateur y dépose, pour le connecteur qui l'utilise, et
rien d'autre.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..logging_setup import get_logger

log = get_logger("connectors.secrets")


class SecretStore:
    """Coffre chiffré des secrets de connecteurs."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.key_path = self.base_dir / "secret.key"
        self.data_path = self.base_dir / "secrets.enc"

    # ─────────────────────────── chiffrement ───────────────────────────

    def _store(self):
        from ..crypto_store import CryptoStore
        return CryptoStore.from_key_file(self.key_path)

    def _load_all(self) -> dict:
        if not self.data_path.is_file():
            return {}
        try:
            raw = self.data_path.read_bytes()
            data = self._store().decrypt_bytes(raw)
            return json.loads(data.decode("utf-8"))
        except Exception:
            log.exception("coffre de secrets illisible (%s)", self.data_path)
            return {}

    def _save_all(self, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        blob = self._store().encrypt_bytes(payload)
        # écriture directe puis restriction des permissions
        self.data_path.write_bytes(blob)
        self._restreindre_permissions()

    def _restreindre_permissions(self) -> bool:
        """Force 0600 sur le coffre ; renvoie False si le système refuse.

        **Pourquoi ne plus avaler l'échec.** Un `except OSError: pass` laissait
        le fichier de secrets avec les permissions du répertoire — donc lisible
        par les autres utilisateurs de la machine — sans qu'aucune trace ne le
        signale. L'échec est maintenant journalisé comme une erreur, et
        `describe()` le remonte pour que l'opérateur le voie.
        """
        try:
            import os

            os.chmod(self.data_path, 0o600)
            return True
        except OSError as exc:
            log.error(
                "impossible de restreindre les permissions de %s (%s) : "
                "le coffre de secrets peut être lisible par d'autres utilisateurs",
                self.data_path, exc,
            )
            return False

    # ─────────────────────────── API ───────────────────────────

    def set(self, connector_id: str, key: str, value: str) -> None:
        if not key or value is None:
            raise ValueError("clé ou valeur de secret vide")
        data = self._load_all()
        data.setdefault(connector_id, {})[key] = str(value)
        self._save_all(data)
        log.info("secret enregistré : connecteur=%s clé=%s", connector_id, key)

    def get(self, connector_id: str, key: str,
            default: str | None = None) -> str | None:
        return self._load_all().get(connector_id, {}).get(key, default)

    def all_for(self, connector_id: str) -> dict:
        """Secrets d'un connecteur. **À ne jamais journaliser ni renvoyer
        via l'API** — l'appelant est responsable de son usage."""
        return dict(self._load_all().get(connector_id, {}))

    def keys_for(self, connector_id: str) -> list[str]:
        """Noms des secrets définis (sans les valeurs) — sûr à exposer."""
        return sorted(self._load_all().get(connector_id, {}))

    def delete(self, connector_id: str, key: str) -> bool:
        data = self._load_all()
        if key in data.get(connector_id, {}):
            del data[connector_id][key]
            self._save_all(data)
            return True
        return False

    def delete_connector(self, connector_id: str) -> bool:
        data = self._load_all()
        if connector_id in data:
            del data[connector_id]
            self._save_all(data)
            return True
        return False

    def describe(self) -> dict:
        """État du coffre — indique quels connecteurs ont des secrets, sans
        jamais révéler ni leur nombre exact de valeur sensible."""
        data = self._load_all()
        perms = self._perms(self.data_path)
        return {
            "encrypted": True,
            "algorithm": "AES-256-GCM",
            "kdf": "PBKDF2-HMAC-SHA256",
            "key_length_bits": 256,
            "path": str(self.data_path),
            "connectors_with_secrets": sorted(data.keys()),
            "key_file_permissions": self._perms(self.key_path),
            # le coffre lui-même : visible par l'opérateur si le chmod a échoué.
            # None = pas encore de fichier (état inconnu, pas « non sûr »).
            "vault_file_permissions": perms,
            "vault_file_secure": (None if perms == "absent" else perms == "0o600"),
        }

    @staticmethod
    def _perms(path: Path) -> str:
        try:
            import os
            return oct(os.stat(path).st_mode & 0o777)
        except OSError:
            return "absent"
