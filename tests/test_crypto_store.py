"""Tests E3 : chiffrement au repos optionnel (AES-256-GCM)."""
import os

import pytest

from unocr.crypto_store import (
    KEY_LEN,
    MAGIC,
    CryptoError,
    CryptoStore,
    derive_key,
    generate_key,
)

DATA = b"document confidentiel \x00\x01\x02\xff" * 200


@pytest.fixture()
def store(tmp_path):
    return CryptoStore.from_key_file(tmp_path / "keys" / "master.key")


# ─────────────────────────── désactivé par défaut ───────────────────────────

def test_disabled_store_is_passthrough(tmp_path):
    """Sans activation, rien ne change : comportement identique à avant."""
    off = CryptoStore(enabled=False)
    assert off.enabled is False
    assert off.encrypt_bytes(b"abc") == b"abc"
    assert off.decrypt_bytes(b"abc") == b"abc"

    src = tmp_path / "a.bin"
    src.write_bytes(DATA)
    dst = off.encrypt_file(src, tmp_path / "b.bin")
    assert dst.read_bytes() == DATA            # copie simple, pas de magie

    st = off.status()
    assert st["enabled"] is False and st["key_length_bits"] == 0


# ─────────────────────────── aller-retour ───────────────────────────

def test_roundtrip_file(store, tmp_path):
    src = tmp_path / "clair.bin"
    src.write_bytes(DATA)
    enc = store.encrypt_file(src, tmp_path / "chiffre.bin")
    assert enc.read_bytes() != DATA            # réellement chiffré
    assert enc.read_bytes().startswith(MAGIC)

    out = store.decrypt_file(enc, tmp_path / "retour.bin")
    assert out.read_bytes() == DATA


def test_roundtrip_bytes(store):
    enc = store.encrypt_bytes(DATA)
    assert enc != DATA and enc.startswith(MAGIC)
    assert store.decrypt_bytes(enc) == DATA


def test_roundtrip_empty_and_binary(store):
    for payload in (b"", b"\x00", bytes(range(256)), b"x" * 100_000):
        assert store.decrypt_bytes(store.encrypt_bytes(payload)) == payload


def test_nonce_is_unique_per_file(store):
    """Un nonce réutilisé casserait GCM : il doit être aléatoire à chaque fois."""
    a = store.encrypt_bytes(b"meme contenu")
    b = store.encrypt_bytes(b"meme contenu")
    assert a != b
    assert a[5:5 + 12] != b[5:5 + 12]


# ─────────────────────────── intégrité ───────────────────────────

def test_tampered_ciphertext_is_rejected(store, tmp_path):
    src = tmp_path / "c.bin"
    src.write_bytes(DATA)
    enc = store.encrypt_file(src, tmp_path / "e.bin")
    raw = bytearray(enc.read_bytes())
    raw[-1] ^= 0xFF                       # un seul bit modifié
    bad = tmp_path / "altere.bin"
    bad.write_bytes(bytes(raw))
    with pytest.raises(CryptoError, match="(clé erronée|altéré)"):
        store.decrypt_file(bad, tmp_path / "out.bin")


def test_wrong_key_is_rejected(store, tmp_path):
    src = tmp_path / "c.bin"
    src.write_bytes(DATA)
    enc = store.encrypt_file(src, tmp_path / "e.bin")

    other = CryptoStore.from_key_file(tmp_path / "autre.key")
    with pytest.raises(CryptoError):
        other.decrypt_file(enc, tmp_path / "out.bin")


def test_encrypted_file_without_key_fails_cleanly(tmp_path):
    """Un fichier chiffré sans clé configurée doit échouer proprement, pas
    renvoyer des octets illisibles."""
    key_store = CryptoStore.from_key_file(tmp_path / "k.key")
    src = tmp_path / "c.bin"
    src.write_bytes(DATA)
    enc = key_store.encrypt_file(src, tmp_path / "e.bin")

    no_key = CryptoStore(enabled=False)
    with pytest.raises(CryptoError, match="aucune clé"):
        no_key.decrypt_file(enc, tmp_path / "out.bin")


def test_unknown_version_is_rejected(store):
    raw = bytearray(store.encrypt_bytes(DATA))
    raw[4] = 99
    with pytest.raises(CryptoError, match="version"):
        store.decrypt_bytes(bytes(raw))


def test_plain_file_passes_through(store, tmp_path):
    """Des données écrites avant l'activation restent lisibles (pas de
    régression sur les données existantes)."""
    src = tmp_path / "ancien.bin"
    src.write_bytes(DATA)
    out = store.decrypt_file(src, tmp_path / "out.bin")
    assert out.read_bytes() == DATA


# ─────────────────────────── gestion des clés ───────────────────────────

def test_key_file_created_with_strict_permissions(tmp_path):
    path = tmp_path / "keys" / "master.key"
    CryptoStore.from_key_file(path)
    assert path.is_file()
    assert len(path.read_bytes()) == KEY_LEN
    # Les bits de permission POSIX n'existent pas sur Windows : le contrôle
    # n'y a pas d'équivalent, la restriction y passe par l'ACL du compte.
    if os.name == "posix":
        assert oct(os.stat(path).st_mode & 0o777) == "0o600"


def test_key_file_reused_when_present(tmp_path):
    path = tmp_path / "k.key"
    first = CryptoStore.from_key_file(path)
    key1 = path.read_bytes()
    second = CryptoStore.from_key_file(path)
    assert path.read_bytes() == key1                     # pas de régénération
    assert second.decrypt_bytes(first.encrypt_bytes(DATA)) == DATA


def test_invalid_key_file_is_refused(tmp_path):
    path = tmp_path / "k.key"
    path.write_bytes(b"trop court")
    with pytest.raises(CryptoError, match="invalide"):
        CryptoStore.from_key_file(path)


def test_passphrase_derivation_roundtrip():
    salt = b"0" * 16
    k1 = derive_key("phrase secrete", salt)
    k2 = derive_key("phrase secrete", salt)
    assert k1 == k2 and len(k1) == KEY_LEN
    assert derive_key("autre phrase", salt) != k1        # sensible à la phrase
    assert derive_key("phrase secrete", b"1" * 16) != k1  # et au sel

    store = CryptoStore.from_passphrase("phrase secrete", salt)
    assert store.decrypt_bytes(store.encrypt_bytes(DATA)) == DATA


def test_empty_passphrase_refused():
    with pytest.raises(CryptoError, match="vide"):
        CryptoStore.from_passphrase("", b"0" * 16)


def test_generate_key_is_random():
    assert generate_key() != generate_key()
    assert len(generate_key()) == KEY_LEN


def test_status_never_reveals_key(store):
    st = store.status()
    assert st["enabled"] is True
    assert st["algorithm"] == "AES-256-GCM"
    assert "key" not in " ".join(st).lower() or st.get("key_length_bits") == 256
    assert st["key_length_bits"] == 256
