from cryptography.fernet import Fernet, InvalidToken

from src.config import get_settings


class TokenEncryptor:
    """Symmetric encryption wrapper for Spotify OAuth tokens.

    Uses Fernet (AES-128-CBC + HMAC-SHA256) with the key from settings.
    The key must be a valid Fernet key — generate one with:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """

    def __init__(self) -> None:
        settings = get_settings()
        key = settings.encryption_key
        # Accept both str and bytes — Fernet requires bytes
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt a string token and return the ciphertext bytes."""
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt ciphertext bytes and return the original string token.

        Raises ValueError if the ciphertext is invalid or the key is wrong.
        """
        try:
            return self._fernet.decrypt(ciphertext).decode()
        except InvalidToken as exc:
            raise ValueError("Token decryption failed — invalid ciphertext or wrong key") from exc
