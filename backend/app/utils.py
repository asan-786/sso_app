from passlib.hash import bcrypt
import hashlib
import os
import base64

def hash_token(token: str) -> str:
    """Hash refresh tokens for DB storage."""
    # You can use bcrypt or sha256 with salt; bcrypt is shown for tokens shorter than password sizes.
    return bcrypt.hash(token)

def verify_token_hash(token: str, hashed: str) -> bool:
    return bcrypt.verify(token, hashed)

def generate_random_token(nbytes: int = 32) -> str:
    return base64.urlsafe_b64encode(os.urandom(nbytes)).decode('utf-8').rstrip('=')
