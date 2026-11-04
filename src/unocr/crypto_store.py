"""Chiffrement au repos optionnel des documents (E3).

**Ce que fait ce module.** Chiffrer en AES-256-GCM les fichiers déposés dans
`data/` (documents sources et résultats), avec une clé :

- soit générée aléatoirement et conservée dans un fichier de clé
  (`data/keys/master.key`, permissions 0600) ;
- soit dérivée d'une phrase de passe (PBKDF2-HMAC-SHA256), ce qui évite de
  stocker la clé à côté des données qu'elle protège.

**Ce qu'il ne fait pas.**

- Il ne chiffre **rien par défaut** : sans `security.encryption.enabled`,
  `CryptoStore` est un passe-plat et l'application se comporte exactement
  comme avant. Aucune donnée existante n'est modifiée à l'insu de l'utilisateur.
- Il ne prétend pas protéger contre un attaquant présent sur la machine au
  moment du traitement : les documents sont déchiffrés en mémoire pour être
  analysés. La protection porte sur le **stockage** (disque, sauvegarde,
  copie de volume).
- Il ne récupère jamais une clé perdue. **Perdre la clé = perdre les données**,
  définitivement. Aucune porte dérobée n'existe et n'en existera.

Format de fichier chiffré : `magic(4) | version(1) | nonce(12) | ciphertext`.
L'authentification GCM détecte toute altération : un octet modifié fait échouer
le déchiffrement au lieu de renvoyer des données corrompues.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from .logging_setup import get_logger

log = get_logger("crypto_store")

MAGIC = b"UOCR"
VERSION = 1
SALT_LEN = 16
NONCE_LEN = 12          # recommandé pour AES-GCM
KEY_LEN = 32            # AES-256
PBKDF2_ITERS = 600_000  # OWASP 2023 pour PBKDF2-HMAC-SHA256


class CryptoError(Exception):
    """Échec de chiffrement/déchiffrement (clé absente, données altérées…)."""


def _aesgcm(key: bytes):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(key)


def generate_key() -> bytes:
    """Clé aléatoire de 256 bits."""
    return secrets.token_bytes(KEY_LEN)


def derive_key(passphrase: str, salt: bytes,
               iters: int = PBKDF2_ITERS) -> bytes:
    """Dérive une clé AES-256 d'une phrase de passe (PBKDF2-HMAC-SHA256)."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=KEY_LEN, salt=salt,
                     iterations=iters)
    return kdf.derive(passphrase.encode("utf-8"))


class CryptoStore:
    """Chiffre/déchiffre des fichiers. Désactivé par défaut (passe-plat)."""

    def __init__(self, key: bytes | None = None, enabled: bool = False):
        self.enabled = enabled and key is not None
        self._key = key

    # ─────────────────────────── clés ───────────────────────────

    @classmethod
    def from_key_file(cls, path: Path) -> "CryptoStore":
        """Charge (ou crée) un fichier de clé aléatoire, permissions 0600."""
        path = Path(path)
        if path.is_file():
            key = path.read_bytes()
            if len(key) != KEY_LEN:
                raise CryptoError(
                    f"fichier de clé invalide : {len(key)} octets "
                    f"(attendu {KEY_LEN})")
            log.info("clé de chiffrement chargée (%s)", path)
            return cls(key=key, enabled=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        key = generate_key()
        # écriture directe puis restriction : évite une fenêtre de lecture
        path.write_bytes(key)
        os.chmod(path, 0o600)
        log.warning("NOUVELLE clé de chiffrement créée (%s) — "
                    "la perdre rend les données définitivement illisibles", path)
        return cls(key=key, enabled=True)

    @classmethod
    def from_passphrase(cls, passphrase: str, salt: bytes) -> "CryptoStore":
        """Dérive la clé d'une phrase de passe (aucun secret stocké)."""
        if not passphrase:
            raise CryptoError("phrase de passe vide")
        if len(salt) != SALT_LEN:
            raise CryptoError(f"sel invalide : {len(salt)} octets")
        return cls(key=derive_key(passphrase, salt), enabled=True)

    # ─────────────────────── fichiers ───────────────────────

    def encrypt_file(self, src: Path, dst: Path) -> Path:
        """Chiffre `src` vers `dst`. Sans activation, copie simple."""
        src, dst = Path(src), Path(dst)
        data = src.read_bytes()
        if not self.enabled:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            return dst
        nonce = secrets.token_bytes(NONCE_LEN)
        ct = _aesgcm(self._key).encrypt(nonce, data, None)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(MAGIC + bytes([VERSION]) + nonce + ct)
        return dst

    def decrypt_file(self, src: Path, dst: Path) -> Path:
        """Déchiffre `src` vers `dst`. Détecte toute altération (GCM)."""
        src, dst = Path(src), Path(dst)
        raw = src.read_bytes()
        if not raw.startswith(MAGIC):
            # fichier en clair (données écrites avant activation)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(raw)
            return dst
        if not self.enabled:
            raise CryptoError(
                "fichier chiffré mais aucune clé configurée : "
                "activez security.encryption avec la bonne clé")
        version = raw[4]
        if version != VERSION:
            raise CryptoError(f"version de chiffrement inconnue : {version}")
        nonce, ct = raw[5:5 + NONCE_LEN], raw[5 + NONCE_LEN:]
        try:
            data = _aesgcm(self._key).decrypt(nonce, ct, None)
        except Exception as exc:
            raise CryptoError(
                "déchiffrement impossible (clé erronée ou fichier altéré)"
            ) from exc
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        return dst

    def encrypt_bytes(self, data: bytes) -> bytes:
        if not self.enabled:
            return data
        nonce = secrets.token_bytes(NONCE_LEN)
        ct = _aesgcm(self._key).encrypt(nonce, data, None)
        return MAGIC + bytes([VERSION]) + nonce + ct

    def decrypt_bytes(self, raw: bytes) -> bytes:
        if not raw.startswith(MAGIC):
            return raw
        if not self.enabled:
            raise CryptoError("données chiffrées sans clé configurée")
        version = raw[4]
        if version != VERSION:
            raise CryptoError(f"version de chiffrement inconnue : {version}")
        nonce, ct = raw[5:5 + NONCE_LEN], raw[5 + NONCE_LEN:]
        try:
            return _aesgcm(self._key).decrypt(nonce, ct, None)
        except Exception as exc:
            raise CryptoError(
                "déchiffrement impossible (clé erronée ou données altérées)"
            ) from exc

    def status(self) -> dict:
        """État exposable par l'API — ne révèle jamais la clé."""
        return {"enabled": self.enabled, "algorithm": "AES-256-GCM",
                "kdf": "PBKDF2-HMAC-SHA256" if self.enabled else None,
                "key_length_bits": 256 if self.enabled else 0}
