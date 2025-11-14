import hashlib
import base64
from cryptography.fernet import Fernet
import os

def hash_file_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def generate_fernet_key():
    return Fernet.generate_key().decode()

def get_fernet(key: str):
    return Fernet(key.encode() if isinstance(key,str) else key)

def encrypt_key(plain: str, fernet_key: str) -> bytes:
    f = get_fernet(fernet_key)
    return f.encrypt(plain.encode())

def decrypt_key(token: bytes, fernet_key: str) -> str:
    f = get_fernet(fernet_key)
    return f.decrypt(token).decode()
