import pytest
from cryptography.fernet import Fernet

from src.utils.token_encryptor import TokenEncryptor


@pytest.fixture
def encryptor(monkeypatch):
    """TokenEncryptor instance using a freshly-generated test key."""
    test_key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", test_key)
    # Clear the lru_cache so the new env var is picked up
    from src.config import get_settings
    get_settings.cache_clear()
    yield TokenEncryptor()
    get_settings.cache_clear()


def test_encrypt_returns_bytes(encryptor):
    result = encryptor.encrypt("some_token")
    assert isinstance(result, bytes)


def test_round_trip(encryptor):
    plaintext = "spotify_access_token_abc123"
    assert encryptor.decrypt(encryptor.encrypt(plaintext)) == plaintext


def test_different_ciphertexts_for_same_input(encryptor):
    """Fernet uses a random IV so each encryption produces a unique ciphertext."""
    token = "same_token"
    assert encryptor.encrypt(token) != encryptor.encrypt(token)


def test_decrypt_wrong_key_raises(monkeypatch):
    key_a = Fernet.generate_key().decode()
    key_b = Fernet.generate_key().decode()

    monkeypatch.setenv("ENCRYPTION_KEY", key_a)
    from src.config import get_settings
    get_settings.cache_clear()
    enc_a = TokenEncryptor()

    monkeypatch.setenv("ENCRYPTION_KEY", key_b)
    get_settings.cache_clear()
    enc_b = TokenEncryptor()

    ciphertext = enc_a.encrypt("secret_token")
    with pytest.raises(ValueError, match="decryption failed"):
        enc_b.decrypt(ciphertext)

    get_settings.cache_clear()


def test_decrypt_tampered_bytes_raises(encryptor):
    ciphertext = encryptor.encrypt("real_token")
    tampered = ciphertext[:-4] + b"xxxx"
    with pytest.raises(ValueError):
        encryptor.decrypt(tampered)
