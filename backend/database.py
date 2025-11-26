import sqlite3, secrets
import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException
import os
import inspect
from .sso_helpers import serialize_redirect_entries, normalize_scopes
from .config import seeded_client_secrets, AUTH_CODE_EXPIRY_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

# CONNECTION AND INITIALISATION
DB_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    "sso_database.db"
)
def get_db_connection():
    conn = sqlite3.connect(DB_FILE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    from .security import pwd_context, generate_client_secret_value, hash_client_secret_value
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table Creations
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
            redirect_url TEXT,
            blocked BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add redirect_url column if the table existed previously without it
    try:
        cursor.execute("ALTER TABLE applications ADD COLUMN redirect_url TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE applications ADD COLUMN blocked BOOLEAN DEFAULT FALSE")
    except sqlite3.OperationalError:
        pass
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_app_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            app_id TEXT NOT NULL,
            blocked BOOLEAN DEFAULT FALSE,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (app_id) REFERENCES applications(id)
        )
    """)
    try:
        cursor.execute("ALTER TABLE user_app_access ADD COLUMN blocked BOOLEAN DEFAULT FALSE")
    except sqlite3.OperationalError:
        pass
    
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
            app_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Ensure legacy databases have app_id column
    try:
        cursor.execute("ALTER TABLE api_keys ADD COLUMN app_id TEXT")
    except sqlite3.OperationalError:
        pass
    
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_consents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            app_id TEXT NOT NULL,
            scopes TEXT NOT NULL,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revoked BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (app_id) REFERENCES applications(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_removal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            user_name TEXT,
            app_id TEXT NOT NULL,
            app_name TEXT,
            removed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_consents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            app_id TEXT NOT NULL,
            redirect_uri TEXT NOT NULL,
            scopes TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (app_id) REFERENCES applications(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorization_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            app_id TEXT NOT NULL,
            scopes TEXT,
            redirect_uri TEXT,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (app_id) REFERENCES applications(id)
        )
    """)
    
    # Seed Default Users
    admin_email = "admin@example.com"
    cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    admin_row = cursor.fetchone()
    if not admin_row:
        admin_password = pwd_context.hash("admin123")
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, roll_no, branch, semester)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Admin User", admin_email, admin_password, "admin", "ADMIN001", "CSE", "N/A"))
        cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
        admin_row = cursor.fetchone()
    admin_id = admin_row[0] if admin_row else None
    
    student_email = "student@example.com"
    cursor.execute("SELECT id FROM users WHERE email = ?", (student_email,))
    if not cursor.fetchone():
        student_password = pwd_context.hash("student123")
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, roll_no, branch, semester)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Student User", student_email, student_password, "student", "23UCSE4001", "CSE", "7"))

    # Seed Default Applications
    def ensure_seed_application(name: str, base_url: str, client_id_value: str, redirect_urls: List[str]):
        cursor.execute("SELECT * FROM applications WHERE client_id = ?", (client_id_value,))
        existing = cursor.fetchone()
        redirect_blob = serialize_redirect_entries(redirect_urls)
        if not existing:
            app_uuid = str(uuid.uuid4())
            client_secret_plain = generate_client_secret_value()
            client_secret_hashed = hash_client_secret_value(client_secret_plain)
            cursor.execute("""
                INSERT INTO applications (id, name, url, client_id, client_secret, redirect_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                app_uuid,
                name,
                base_url,
                client_id_value,
                client_secret_hashed,
                redirect_blob,
            ))
            seeded_client_secrets.append((name, client_id_value, client_secret_plain))
        else:
            cursor.execute("""
                UPDATE applications
                SET redirect_url = ?, url = ?
                WHERE client_id = ?
            """, (redirect_blob, base_url, client_id_value))
            if not existing["client_secret"]:
                client_secret_plain = generate_client_secret_value()
                client_secret_hashed = hash_client_secret_value(client_secret_plain)
                cursor.execute("""
                    UPDATE applications
                    SET client_secret = ?
                    WHERE id = ?
                """, (client_secret_hashed, existing["id"]))
                seeded_client_secrets.append((name, client_id_value, client_secret_plain))

    ensure_seed_application(
        "CampusConnect Demo",
        "http://127.0.0.1:8080",
        "campusconnect-client",
        [
            "http://127.0.0.1:5501/third_party_app/index.html",
            "http://127.0.0.1:5501/sso_app/third_party_app/index.html",
        ],
    )

    ensure_seed_application(
        "CampusConnect Plus Demo",
        "http://127.0.0.1:8081",
        "campusconnect-client-2",
        [
            "http://127.0.0.1:5500/third_party_app_2/index2.html",
            "http://127.0.0.1:5500/sso_app/third_party_app_2/index2.html",
        ],
    )

    # Seed demo API keys for both applications (owned by admin for convenience)
    if admin_id:
        demo_api_keys = [
            ("CampusConnect Demo Key", "sso_live_cc_demo_primary_4d2d59"),
            ("CampusConnect Plus Demo Key", "sso_live_cc_plus_primary_a13b78"),
        ]
        for name, key_value in demo_api_keys:
            cursor.execute("""
                SELECT id FROM api_keys WHERE key_value = ? AND user_id = ?
            """, (key_value, admin_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO api_keys (key_value, user_id, name)
                    VALUES (?, ?, ?)
                """, (key_value, admin_id, name))
    
    conn.commit()
    conn.close()

    if seeded_client_secrets:
        print("\n[SSO] Generated client secrets for seeded applications (store these securely):")
        for app_name, client_id_value, secret_value in seeded_client_secrets:
            print(f" - {app_name} [{client_id_value}]: {secret_value}")

# User/App Access Functions
def ensure_user_app_access(user_email: str, app_id: str) -> None:
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM user_app_access
        WHERE user_email = ? AND app_id = ?
    """, (user_email, app_id))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO user_app_access (user_email, app_id, blocked)
            VALUES (?, ?, FALSE)
        """, (user_email, app_id))
        conn.commit()
    conn.close()

def is_user_blocked_for_app(user_email: str, app_id: str) -> bool:
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT blocked FROM user_app_access
        WHERE user_email = ? AND app_id = ?
    """, (user_email, app_id))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    return bool(row["blocked"])

# User Lookup Functions
def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# Application Lookup Functions
def get_application_by_client_id(client_id: str) -> Optional[sqlite3.Row]:
    if not client_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE client_id = ?", (client_id,))
    app = cursor.fetchone()
    conn.close()
    return dict(app) if app else None

def get_application_by_id(app_id: str) -> Optional[sqlite3.Row]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    app = cursor.fetchone()
    conn.close()
    return dict(app) if app else None

# Consent Functions
def user_has_consent(user_id: int, app_id: str, requested_scopes: List[str]) -> bool:
    if not requested_scopes:
        return True

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, scopes FROM user_consents
        WHERE user_id = ? AND app_id = ? AND revoked = FALSE
    """, (user_id, app_id))
    consents = cursor.fetchall()
    conn.close()

    requested = set(requested_scopes)
    for consent in consents:
        existing = set(normalize_scopes(consent["scopes"]))
        if requested.issubset(existing):
            return True
    return False

def save_user_consent(user_id: int, app_id: str, scopes: List[str]) -> None:
    normalized = normalize_scopes(" ".join(scopes))
    if not normalized:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, scopes FROM user_consents
        WHERE user_id = ? AND app_id = ?
        ORDER BY id DESC LIMIT 1
    """, (user_id, app_id))
    existing = cursor.fetchone()

    if existing:
        existing_scopes = set(normalize_scopes(existing["scopes"]))
        merged = sorted(existing_scopes.union(normalized))
        cursor.execute("""
            UPDATE user_consents
            SET scopes = ?, revoked = FALSE, granted_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (" ".join(merged), existing["id"]))
    else:
        cursor.execute("""
            INSERT INTO user_consents (user_id, app_id, scopes)
            VALUES (?, ?, ?)
        """, (user_id, app_id, " ".join(normalized)))

    conn.commit()
    cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    conn.close()

    if user_row and user_row["email"]:
        ensure_user_app_access(user_row["email"], app_id)

# Pending Consent Functions
def create_pending_consent(user_id: int, app_id: str, redirect_uri: str, scopes: List[str]) -> str:
    token = secrets.token_urlsafe(48)
    expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pending_consents (token, user_id, app_id, redirect_uri, scopes, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (token, user_id, app_id, redirect_uri, " ".join(scopes), expires_at))
    conn.commit()
    conn.close()

    return token

def get_pending_consent(token: str) -> Optional[sqlite3.Row]:
    if not token:
        return None

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pc.*, u.email AS user_email, a.name AS app_name
        FROM pending_consents pc
        JOIN users u ON pc.user_id = u.id
        JOIN applications a ON pc.app_id = a.id
        WHERE pc.token = ?
    """, (token,))
    row = cursor.fetchone()
    conn.close()
    return row

def delete_pending_consent(token: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_consents WHERE token = ?", (token,))
    conn.commit()
    conn.close()

# Authorization Code Functions
def create_authorization_code(user_id: int, app_id: str, scopes: List[str], redirect_uri: str) -> str:
    code = secrets.token_urlsafe(40)
    expires_at = (datetime.utcnow() + timedelta(minutes=AUTH_CODE_EXPIRY_MINUTES)).isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO authorization_codes (code, user_id, app_id, scopes, redirect_uri, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (code, user_id, app_id, " ".join(scopes), redirect_uri, expires_at))
    conn.commit()
    conn.close()
    return code

def consume_authorization_code(code: str) -> Optional[sqlite3.Row]:
    if not code:
        return None

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM authorization_codes WHERE code = ?
    """, (code,))
    record = cursor.fetchone()
    if not record:
        conn.close()
        return None

    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.utcnow() > expires_at or record["used"]:
        cursor.execute("UPDATE authorization_codes SET used = TRUE WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        return None

    cursor.execute("""
        UPDATE authorization_codes
        SET used = TRUE, used_at = CURRENT_TIMESTAMP
        WHERE code = ?
    """, (code,))
    conn.commit()
    conn.close()
    return record

# Refresh Tokens Functions
def create_refresh_token(user_id: int):
    token_value = secrets.token_urlsafe(64)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    conn = get_db_connection()
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
    conn = get_db_connection()
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
    
    # Check for expiration
    expires_at = datetime.fromisoformat(result["expires_at"])
    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    return result["user_id"]

# Logging Functions
def log_app_removal(user_email: str, user_name: str, app_id: str, app_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO app_removal_logs (user_email, user_name, app_id, app_name)
        VALUES (?, ?, ?, ?)
    """, (user_email, user_name, app_id, app_name))
    conn.commit()
    conn.close()


# init_db()