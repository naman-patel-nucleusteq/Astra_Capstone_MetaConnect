from cryptography.fernet import Fernet
from app.core.config import ENCRYPTION_KEY
import os


def get_cipher():
    if not ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is not configured")

    return Fernet(ENCRYPTION_KEY.encode())


def encrypt_password(password: str) -> str:
    cipher = get_cipher()
    return cipher.encrypt(password.encode()).decode()


def decrypt_password(encrypted_password: str) -> str:
    cipher = get_cipher()
    return cipher.decrypt(encrypted_password.encode()).decode()