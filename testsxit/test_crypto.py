import pytest
from tool_loader.security import CryptoManager
from tool_loader.exceptions import DecryptionError, EncryptionError


@pytest.fixture
def crypto() -> CryptoManager:
    key = CryptoManager.generate_key()
    return CryptoManager(key=key)


def test_roundtrip(crypto: CryptoManager) -> None:
    original = {"API_KEY": "secret-123", "DB_PASS": "hunter2"}
    token = crypto.encrypt_env_vars(original)
    assert isinstance(token, str)
    recovered = crypto.decrypt_env_vars(token)
    assert recovered == original


def test_empty_dict(crypto: CryptoManager) -> None:
    token = crypto.encrypt_env_vars({})
    assert crypto.decrypt_env_vars(token) == {}


def test_tampered_token_raises(crypto: CryptoManager) -> None:
    token = crypto.encrypt_env_vars({"k": "v"})
    bad_token = token[:-4] + "XXXX"
    with pytest.raises(DecryptionError):
        crypto.decrypt_env_vars(bad_token)


def test_bad_key_raises() -> None:
    with pytest.raises(EncryptionError):
        CryptoManager(key=b"not-a-valid-key")
