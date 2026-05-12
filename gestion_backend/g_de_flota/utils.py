from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib

def get_cipher():
    key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

def encrypt_value(value):
    if value is None:
        return value
    return get_cipher().encrypt(value.encode()).decode()

def decrypt_value(value):
    if value is None:
        return value
    return get_cipher().decrypt(value.encode()).decode()