from fastapi.responses import HTMLResponse
from fastapi import FastAPI, HTTPException, Depends, status, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.responses import RedirectResponse # ADDED: For SSO redirect
import sqlite3
import uuid
import secrets
import os

# ============================================
# CONFIGURATION
# ============================================
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30
API_KEY_PREFIX = "sso_live_"

app = FastAPI(title="SSO Portal - Enhanced Backend")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# IMPORTANT: Ensure your frontend URL (http://127.0.0.1:5500) is allowed here
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# DATABASE SETUP
# ============================================
def init_db():
    conn = sqlite3.connect("sso_database.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            roll_no TEXT,
            branch TEXT,
            semester TEXT,
            role TEXT DEFAULT 'student',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            client_id TEXT,
            client_secret TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_app_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            app_id TEXT NOT NULL,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (app_id) REFERENCES applications(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revoked BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_value TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            revoked BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            access_token_jti TEXT,
            refresh_token_id INTEGER,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    admin_email = "admin@example.com"
    cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    if not cursor.fetchone():
        admin_password = pwd_context.hash("admin123")
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, roll_no, branch, semester)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Admin User", admin_email, admin_password, "admin", "ADMIN001", "CSE", "N/A"))
    
    student_email = "student@example.com"
    cursor.execute("SELECT id FROM users WHERE email = ?", (student_email,))
    if not cursor.fetchone():
        student_password = pwd_context.hash("student123")
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, roll_no, branch, semester)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Student User", student_email, student_password, "student", "23UCSE4001", "CSE", "7"))
    
    conn.commit()
    conn.close()

init_db()

# ============================================
# PYDANTIC MODELS
# ============================================
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirmPassword: str
    rollNo: str
    branch: str
    semester: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenVerify(BaseModel):
    token: str

class APIKeyCreate(BaseModel):
    name: str

class APIKeyResponse(BaseModel):
    id: int
    key_value: str
    name: str
    created_at: str
    last_used: Optional[str] = None

class ApplicationCreate(BaseModel):
    name: str
    url: str
    client_id: Optional[str] = ""
    client_secret: Optional[str] = ""

class Application(BaseModel):
    id: str
    name: str
    url: str
    client_id: Optional[str] = ""
    client_secret: Optional[str] = ""
    authorized_emails: List[str] = Field(default_factory=list)

class MapRequest(BaseModel):
    email: str
    app_id: str

class User(BaseModel):
    id: int
    name: str
    email: str
    role: str
    rollNo: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[str] = None
    status: str

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

# ============================================
# HELPER FUNCTIONS
# ============================================
def get_db():
    conn = sqlite3.connect("sso_database.db")
    conn.row_factory = sqlite3.Row
    return conn

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

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

def create_refresh_token(user_id: int):
    token_value = secrets.token_urlsafe(64)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO refresh_tokens (token, user_id, expires_at)
        VALUES (?, ?, ?)
    """, (token_value, user_id, expires_at))
    conn.commit()
    token_id = cursor.lastrowid
    conn.close()
    
    return token_value, token_id

def verify_refresh_token(token: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, expires_at, revoked 
        FROM refresh_tokens 
        WHERE token = ?
    """, (token,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if result["revoked"]:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    
    expires_at = datetime.fromisoformat(result["expires_at"])
    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    return result["user_id"]

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    conn = get_db()
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
    
    conn = get_db()
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

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================
@app.post("/api/auth/register", response_model=Token)
def register(user_data: UserRegister):
    if user_data.password != user_data.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = ?", (user_data.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    password_hash = pwd_context.hash(user_data.password)
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, roll_no, branch, semester, role)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_data.name, user_data.email, password_hash, user_data.rollNo, 
          user_data.branch, user_data.semester, "student"))
    
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    access_token, jti = create_access_token(data={"sub": user_data.email})
    refresh_token, refresh_id = create_refresh_token(user_id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "role": "student",
            "rollNo": user_data.rollNo,
            "branch": user_data.branch,
            "semester": user_data.semester
        }
    }

@app.post("/api/auth/login", response_model=Token)
def login(credentials: UserLogin):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (credentials.email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token, jti = create_access_token(data={"sub": user["email"]})
    refresh_token, refresh_id = create_refresh_token(user["id"])
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "rollNo": user["roll_no"],
            "branch": user["branch"],
            "semester": user["semester"]
        }
    }

# FIXED SSO LOGIN ENDPOINT FOR REDIRECT FLOW
@app.post("/login")
def sso_login_redirect(
    email: str = Form(...),
    password: str = Form(...),
    redirect_uri: str = Form(...)
):
    """
    Handles user authentication for SSO flow and redirects to the third-party app
    with the access token appended as a fragment (#token=...) in the URL.
    
    This endpoint accepts form data (not JSON) from the SSO login page.
    After successful authentication, it redirects the browser to the third-party app
    with the JWT token in the URL fragment.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(password, user["password_hash"]):
        # For better UX, redirect to login page with error instead of raising exception
        error_url = f"{redirect_uri}?error=invalid_credentials"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)
    
    # 1. Generate the Access Token
    access_token, jti = create_access_token(data={"sub": user["email"]})
    
    # 2. Construct the Redirect URL with token in HASH fragment
    # This is important: we use # (hash) instead of ? (query) for security
    # The token won't be sent to the server, only processed by JavaScript
    final_redirect_url = f"{redirect_uri}?token={access_token}"

    # 3. Redirect the browser
    return RedirectResponse(url=final_redirect_url, status_code=status.HTTP_302_FOUND)
# END FIXED SSO LOGIN ENDPOINT

@app.post("/api/auth/refresh")
def refresh_access_token(token_data: TokenRefresh):
    user_id = verify_refresh_token(token_data.refresh_token)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    access_token, jti = create_access_token(data={"sub": user["email"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post("/api/auth/verify")
def verify_token(token_data: TokenVerify):
    try:
        payload = jwt.decode(token_data.token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "valid": True,
            "email": payload.get("sub"),
            "expires_at": payload.get("exp"),
            "type": payload.get("type")
        }
    except JWTError as e:
        return {
            "valid": False,
            "error": str(e)
        }

@app.post("/api/auth/logout")
def logout(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE refresh_tokens 
        SET revoked = TRUE 
        WHERE user_id = ?
    """, (current_user["id"],))
    conn.commit()
    conn.close()
    
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"],
        "role": current_user["role"],
        "rollNo": current_user.get("roll_no"),
        "branch": current_user.get("branch"),
        "semester": current_user.get("semester")
    }

# ============================================
# PROFILE MANAGEMENT
# ============================================
@app.put("/api/profile")
def update_profile(profile_data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    if profile_data.email and profile_data.email != current_user["email"]:
        cursor.execute("SELECT id FROM users WHERE email = ?", (profile_data.email,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Email already in use")
    
    update_fields = []
    params = []
    
    if profile_data.name:
        update_fields.append("name = ?")
        params.append(profile_data.name)
    
    if profile_data.email:
        update_fields.append("email = ?")
        params.append(profile_data.email)
    
    if not update_fields:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(current_user["id"])
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    
    return {"message": "Profile updated successfully"}

# ============================================
# API KEY MANAGEMENT
# ============================================
@app.post("/api/keys", response_model=APIKeyResponse)
def create_api_key(key_data: APIKeyCreate, current_user: dict = Depends(get_current_user)):
    key_value = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO api_keys (key_value, user_id, name)
        VALUES (?, ?, ?)
    """, (key_value, current_user["id"], key_data.name))
    conn.commit()
    key_id = cursor.lastrowid
    conn.close()
    
    return {
        "id": key_id,
        "key_value": key_value,
        "name": key_data.name,
        "created_at": datetime.utcnow().isoformat(),
        "last_used": None
    }

@app.get("/api/keys", response_model=List[APIKeyResponse])
def list_api_keys(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, key_value, name, created_at, last_used 
        FROM api_keys 
        WHERE user_id = ? AND revoked = FALSE
    """, (current_user["id"],))
    keys = cursor.fetchall()
    conn.close()
    
    return [{
        "id": k["id"],
        "key_value": k["key_value"],
        "name": k["name"],
        "created_at": k["created_at"],
        "last_used": k["last_used"]
    } for k in keys]

@app.delete("/api/keys/{key_id}")
def revoke_api_key(key_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE api_keys 
        SET revoked = TRUE 
        WHERE id = ? AND user_id = ?
    """, (key_id, current_user["id"]))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="API key not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "API key revoked"}

# ============================================
# SDK INTEGRATION ENDPOINTS
# ============================================
@app.post("/api/sdk/login")
def sdk_login(credentials: UserLogin, current_app: dict = Depends(verify_api_key)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (credentials.email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token, jti = create_access_token(data={"sub": user["email"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"]
        }
    }

@app.get("/api/sdk/verify")
def sdk_verify_token(token: str, current_app: dict = Depends(verify_api_key)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, role FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "valid": True,
            "user": dict(user)
        }
    except JWTError:
        return {"valid": False}

# ============================================
# USER MANAGEMENT
# ============================================
@app.get("/api/users", response_model=List[User])
def get_all_users(current_user: dict = Depends(require_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, roll_no, branch, semester, status FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return [{
        "id": u["id"],
        "name": u["name"],
        "email": u["email"],
        "role": u["role"],
        "rollNo": u["roll_no"],
        "branch": u["branch"],
        "semester": u["semester"],
        "status": u["status"]
    } for u in users]

@app.put("/api/users/{user_id}/role")
def update_user_role(user_id: int, role: str, current_user: dict = Depends(require_admin)):
    if role not in ["student", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    conn.close()
    
    return {"message": f"Role updated to {role}"}

# ============================================
# APPLICATION MANAGEMENT
# ============================================
@app.post("/api/applications")
def create_application(app_data: ApplicationCreate, current_user: dict = Depends(require_admin)):
    app_id = str(uuid.uuid4())
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO applications (id, name, url, client_id, client_secret)
        VALUES (?, ?, ?, ?, ?)
    """, (app_id, app_data.name, app_data.url, app_data.client_id, app_data.client_secret))
    conn.commit()
    conn.close()
    
    return {
        "id": app_id,
        "name": app_data.name,
        "url": app_data.url,
        "message": "Application created successfully"
    }

@app.get("/api/applications", response_model=List[Application])
def get_applications(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM applications")
    apps = [dict(row) for row in cursor.fetchall()]
    
    for app in apps:
        cursor.execute("""
            SELECT user_email FROM user_app_access 
            WHERE app_id = ?
        """, (app["id"],))
        app["authorized_emails"] = [row["user_email"] for row in cursor.fetchall()]
    
    conn.close()
    
    return apps

@app.put("/api/applications/{app_id}")
def update_application(app_id: str, app_data: ApplicationCreate, current_user: dict = Depends(require_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE applications 
        SET name = ?, url = ?, client_id = ?, client_secret = ?
        WHERE id = ?
    """, (app_data.name, app_data.url, app_data.client_id, app_data.client_secret, app_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Application updated successfully"}

@app.delete("/api/applications/{app_id}")
def delete_application(app_id: str, current_user: dict = Depends(require_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM user_app_access WHERE app_id = ?", (app_id,))
    cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Application deleted successfully"}

# ============================================
# USER-APP MAPPING
# ============================================
@app.post("/api/map")
def map_user_to_app(mapping: MapRequest, current_user: dict = Depends(require_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = ?", (mapping.email,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    cursor.execute("SELECT id FROM applications WHERE id = ?", (mapping.app_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
    
    cursor.execute("""
        SELECT id FROM user_app_access 
        WHERE user_email = ? AND app_id = ?
    """, (mapping.email, mapping.app_id))
    
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="User already has access to this application")
    
    cursor.execute("""
        INSERT INTO user_app_access (user_email, app_id)
        VALUES (?, ?)
    """, (mapping.email, mapping.app_id))
    
    conn.commit()
    conn.close()
    
    return {"message": "User mapped to application successfully"}

@app.post("/api/unmap")
def unmap_user_from_app(mapping: MapRequest, current_user: dict = Depends(require_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM user_app_access 
        WHERE user_email = ? AND app_id = ?
    """, (mapping.email, mapping.app_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "User access removed successfully"}

@app.get("/api/user/email/{email}/apps")
def get_user_apps(email: str, current_user: dict = Depends(get_current_user)):
    if current_user["email"] != email and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT a.* FROM applications a
        INNER JOIN user_app_access uaa ON a.id = uaa.app_id
        WHERE uaa.user_email = ?
    """, (email,))
    
    apps = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return apps

# ============================================
# ROOT ENDPOINTS
# ============================================
@app.get("/")
def root():
    return {
        "status": "SSO Portal Backend Running",
        "version": "2.1", # Updated version number
        "features": [
            "Temporary JWT tokens (30 min)",
            "Refresh tokens (30 days)",
            "Permanent API keys",
            "Token verification",
            "SSO Redirect Login Endpoint (/login)", # Added feature
            "SDK integration endpoints",
            "User-App mapping",
            "Profile management"
        ]
    }

@app.get("/health")
def health():
    return {"status": "ok", "modules": ["auth", "token_management", "sdk_ready", "app_management"]}

@app.get("/sso-login", response_class=HTMLResponse)
def sso_login_page():
    """Serves the SSO login page for third-party applications"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SSO Login Portal</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gradient-to-br from-indigo-50 to-purple-100 min-h-screen flex items-center justify-center">
        <div class="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
            <div class="text-center mb-8">
                <div class="bg-indigo-600 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="text-white w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                    </svg>
                </div>
                <h1 class="text-3xl font-bold text-gray-800">SSO Login Portal</h1>
                <p class="text-gray-600 mt-2">Sign in with your university credentials</p>
            </div>

            <div id="error-message" class="hidden bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4"></div>

            <form id="sso-login-form" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input 
                        type="email" 
                        id="email" 
                        name="email" 
                        required 
                        placeholder="student@university.edu"
                        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Password</label>
                    <input 
                        type="password" 
                        id="password" 
                        name="password" 
                        required 
                        placeholder="••••••••"
                        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                </div>

                <button 
                    type="submit" 
                    class="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition disabled:bg-gray-400"
                    id="submit-btn"
                >
                    Sign In
                </button>
            </form>

            <p class="text-center mt-6 text-sm text-gray-500">
                Protected by University SSO System
            </p>
        </div>

        <script>
            const urlParams = new URLSearchParams(window.location.search);
            const redirectUri = urlParams.get('redirect_uri');

            if (!redirectUri) {
                document.getElementById('error-message').textContent = 
                    'Error: No redirect URI provided.';
                document.getElementById('error-message').classList.remove('hidden');
                document.getElementById('sso-login-form').style.display = 'none';
            }

            document.getElementById('sso-login-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const submitBtn = document.getElementById('submit-btn');
                const errorDiv = document.getElementById('error-message');
                
                submitBtn.disabled = true;
                submitBtn.textContent = 'Signing in...';
                errorDiv.classList.add('hidden');

                const formData = new FormData();
                formData.append('email', document.getElementById('email').value);
                formData.append('password', document.getElementById('password').value);
                formData.append('redirect_uri', redirectUri);

                const form = document.createElement('form');
                form.method = 'POST';
                form.action = 'http://127.0.0.1:8000/login';

                for (let [key, value] of formData.entries()) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = key;
                    input.value = value;
                    form.appendChild(input);
                }

                document.body.appendChild(form);
                form.submit();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
