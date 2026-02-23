"""
Encryption helper for sensitive settings.
Uses Fernet symmetric encryption.
"""

from cryptography.fernet import Fernet
from app.config import settings

def _get_fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        # Fallback for local dev if key is missing (not recommended for prod)
        # In prod, this will fail early or use a provided key.
        return None
    return Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_value(value: str) -> str:
    """Encrypt a string and return a base64 string."""
    f = _get_fernet()
    if not f:
        return value  # No encryption if key is missing
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a base64 string and return the original string."""
    f = _get_fernet()
    if not f or not encrypted_value:
        return encrypted_value
    try:
        return f.decrypt(encrypted_value.encode()).decode()
    except Exception:
        # If decryption fails (e.g. key changed), return placeholder or error
        return "[Decryption Failed]"
