import json
import os
from typing import Dict

from cryptography.fernet import Fernet, InvalidToken

from tool_loader.exceptions import DecryptionError, EncryptionError

_ENV_KEY = "TOOL_LOADER_FERNET_KEY"


class CryptoManager:
    """Handles symmetric (Fernet) encryption/decryption of env_var dicts."""

    def __init__(self, key: bytes | None = None) -> None:
        if key is None:
            raw = os.environ.get(_ENV_KEY)
            if not raw:
                raise EncryptionError(
                    f"Fernet key not provided and {_ENV_KEY} env var is not set."
                )
            key = raw.encode()
        try:
            self._fernet = Fernet(key)
        except Exception as exc:
            raise EncryptionError(f"Invalid Fernet key: {exc}") from exc

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def encrypt_env_vars(self, env_vars: Dict[str, str]) -> str:
        """Serialize env_vars dict to JSON then encrypt, returning a str token."""
        try:
            plaintext = json.dumps(env_vars).encode()
            return self._fernet.encrypt(plaintext).decode()
        except Exception as exc:
            raise EncryptionError(f"Encryption failed: {exc}") from exc

    def decrypt_env_vars(self, token: str) -> Dict[str, str]:
        """Decrypt a Fernet token back to an env_vars dict."""
        try:
            plaintext = self._fernet.decrypt(token.encode())
            return json.loads(plaintext)
        except InvalidToken as exc:
            raise DecryptionError("Invalid or tampered Fernet token.") from exc
        except Exception as exc:
            raise DecryptionError(f"Decryption failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Key utilities
    # ------------------------------------------------------------------

    @staticmethod
    def generate_key() -> bytes:
        """Generate a fresh URL-safe base64-encoded 32-byte Fernet key."""
        return Fernet.generate_key()
