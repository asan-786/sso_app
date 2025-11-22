from fastapi import HTTPException, Depends, Header
import secrets
from typing import Optional, List
import sqlite3
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import uuid
import os
from .config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    CLIENT_SECRET_BYTES,
    SCOPE_FIELD_MAP
)
from .database import get_db_connection


# The security object definitions
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
client_secret_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
JWT_DECODE_OPTIONS = {"verify_aud": False}

# PASSWORD AND SECRET MANAGEMENT
def generate_client_secret_value() -> str:
    # token_urlsafe roughly adds 4/3 characters per byte; trim for readability
    return secrets.token_urlsafe(CLIENT_SECRET_BYTES)[:64]

def hash_client_secret_value(secret: str) -> str:
    return client_secret_context.hash(secret)

def verify_client_secret_value(secret: str, hashed: Optional[str]) -> bool:
    if not secret or not hashed:
        return False
    try:
        return client_secret_context.verify(secret, hashed)
    except ValueError:
        return False
    
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# JWT TOKEN MANAGEMENT
def filter_user_data_by_scopes(user_row: sqlite3.Row, scopes: List[str]) -> dict:
    allowed_scopes = set(scopes)
    payload = {"id": user_row["id"]}

    for scope in allowed_scopes:
        fields = SCOPE_FIELD_MAP.get(scope, [])
        for field in fields:
            payload[field if field != "roll_no" else "rollNo"] = user_row[field]

    # Always include name if nothing else (basic identifier)
    if "name" not in payload:
        payload["name"] = user_row["name"]

    return payload

def build_user_claims(name: str, email: str, roll_no: Optional[str], branch: Optional[str], semester: Optional[str]):
    return {
        "name": name,
        "email": email,
        "rollNo": roll_no,
        "branch": branch,
        "semester": semester
    }

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, to_encode["jti"]

# FASTAPI DEPENDENCIES
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options=JWT_DECODE_OPTIONS)
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return dict(user)

def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, revoked FROM api_keys 
        WHERE key_value = ?
    """, (x_api_key,))
    result = cursor.fetchone()
    
    if not result or result["revoked"]:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    
    cursor.execute("""
        UPDATE api_keys SET last_used = CURRENT_TIMESTAMP
        WHERE key_value = ?
    """, (x_api_key,))
    conn.commit()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (result["user_id"],))
    user = cursor.fetchone()
    conn.close()
    
    return dict(user)

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
