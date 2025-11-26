from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, HTTPException, Depends, status, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import uuid
import sqlite3
from .schemas import (
    User,
    Token,
    UserInDB,
    UserRegister,
    UserLogin,
    OAuthTokenRequest,
    TokenRefresh,
    TokenVerify,
    ProfileUpdate,
    APIKeyCreate,
    APIKeyResponse,
    ApplicationCreate,        
    ApplicationBlockRequest,  
    ClientSecretRotateResponse, 
    ApplicationUserBlockRequest, 
    ApplicationAPIKeyCreate,   
    Application,
    MapRequest
)
from .security import (
    get_current_user,
    security, pwd_context,
    create_access_token,
    verify_password,
    verify_client_secret_value,
    JWT_DECODE_OPTIONS,
    verify_api_key,
    filter_user_data_by_scopes,
    require_admin,
    generate_client_secret_value,
    hash_client_secret_value,
)
from .config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_SSO_SCOPES,
    SECRET_KEY,
    ALGORITHM,
    API_KEY_PREFIX,
    FRONTEND_REGISTER_URL
)
from .database import (
    init_db,
    get_db_connection, 
    create_refresh_token, 
    get_application_by_client_id, 
    ensure_user_app_access,
    is_user_blocked_for_app,
    user_has_consent,
    create_pending_consent,
    get_pending_consent, 
    delete_pending_consent,
    get_user_by_email, 
    get_application_by_id,
    save_user_consent,
    consume_authorization_code, 
    get_user_by_id,
    verify_refresh_token,
    log_app_removal
)
from .sso_helpers import (
    REDIRECT_SPLIT_PATTERN, 
    append_query_params_to_url, 
    parse_redirect_entries, 
    normalize_redirect_field,
    normalize_scopes,           
    scopes_to_string,           
    normalize_url_for_validation,
    urls_match,                   
    is_redirect_allowed,          
    get_allowed_redirects_for_app,
    build_consent_page,
    serialize_redirect_entries
)

app = FastAPI(title="SSO Portal - Enhanced Backend")

# IMPORTANT: Ensure your frontend URL (http://127.0.0.1:5500) is allowed here
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://127.0.0.1:5500", "http://127.0.0.1:5501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ROOT ENDPOINTS
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
                <p class="text-center text-sm text-gray-500">
                    New here?
                    <button type="button" id="register-link" class="text-indigo-600 font-semibold hover:underline">
                        Create an account
                    </button>
                </p>
            </form>

            <p class="text-center mt-6 text-sm text-gray-500">
                Protected by University SSO System
            </p>
        </div>

        <script>
            const urlParams = new URLSearchParams(window.location.search);
            const redirectUri = urlParams.get('redirect_uri');
            const clientId = urlParams.get('client_id');
            const scopeParam = urlParams.get('scope') || 'profile email';

            const loginForm = document.getElementById('sso-login-form');
            const errorDiv = document.getElementById('error-message');

            if (!redirectUri || !clientId) {
                errorDiv.textContent = 'Error: Missing redirect_uri or client_id.';
                errorDiv.classList.remove('hidden');
                loginForm.style.display = 'none';
            }

            document.getElementById('register-link').addEventListener('click', () => {
                window.location.href = "__FRONTEND_REGISTER_URL__";
            });

            loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const submitBtn = document.getElementById('submit-btn');
                
                submitBtn.disabled = true;
                submitBtn.textContent = 'Signing in...';
                errorDiv.classList.add('hidden');

                const formData = new FormData();
                formData.append('email', document.getElementById('email').value);
                formData.append('password', document.getElementById('password').value);
                formData.append('redirect_uri', redirectUri);

                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '/login';

                for (let [key, value] of formData.entries()) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = key;
                    input.value = value;
                    form.appendChild(input);
                }

                const clientIdField = document.createElement('input');
                clientIdField.type = 'hidden';
                clientIdField.name = 'client_id';
                clientIdField.value = clientId;
                form.appendChild(clientIdField);

                const scopeField = document.createElement('input');
                scopeField.type = 'hidden';
                scopeField.name = 'scope';
                scopeField.value = scopeParam;
                form.appendChild(scopeField);

                document.body.appendChild(form);
                form.submit();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content.replace("__FRONTEND_REGISTER_URL__", FRONTEND_REGISTER_URL))

# AUTHENTICATION ENDPOINTS
@app.post("/api/auth/register", response_model=Token)
def register(user_data: UserRegister):
    if user_data.password != user_data.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    conn = get_db_connection()
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
    conn = get_db_connection()
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

@app.post("/login")
def sso_login_redirect(
    email: str = Form(...),
    password: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    scope: Optional[str] = Form("profile email")
):
    """
    Handles user authentication for SSO flow and redirects to the third-party app
    with the access token appended as a fragment (#token=...) in the URL.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(password, user["password_hash"]):
        # For better UX, redirect to login page with error instead of raising exception
        error_url = f"{redirect_uri}?error=invalid_credentials"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)
    
    application = get_application_by_client_id(client_id)
    if not application:
        raise HTTPException(status_code=400, detail="Unknown client_id")

    # Enforce that the redirect_uri matches one of the registered application origins
    allowed_redirects = get_allowed_redirects_for_app(application)
    redirect_ok = any(is_redirect_allowed(redirect_uri, allowed) for allowed in allowed_redirects)
    if not redirect_ok:
        raise HTTPException(
            status_code=400,
            detail="Invalid redirect_uri for this client application",
        )

    if application.get("blocked"):
        blocked_url = f"{redirect_uri}?error=app_blocked"
        return RedirectResponse(url=blocked_url, status_code=status.HTTP_302_FOUND)

    requested_scopes = normalize_scopes(scope) or DEFAULT_SSO_SCOPES

    ensure_user_app_access(user["email"], application["id"])
    if is_user_blocked_for_app(user["email"], application["id"]):
        blocked_url = f"{redirect_uri}?error=user_blocked"
        return RedirectResponse(url=blocked_url, status_code=status.HTTP_302_FOUND)

    if not user_has_consent(user["id"], application["id"], requested_scopes):
        consent_token = create_pending_consent(
            user_id=user["id"],
            app_id=application["id"],
            redirect_uri=redirect_uri,
            scopes=requested_scopes
        )
        consent_page = build_consent_page(consent_token, application["name"], requested_scopes)
        return HTMLResponse(content=consent_page)

    # 1. Generate the Access Token
    access_token, jti = create_access_token(
        data={
            "sub": user["email"],
            "aud": application["id"],
            "scopes": requested_scopes
        }
    )
    
    # 2. Construct the Redirect URL with token in HASH fragment
    # This is important: we use # (hash) instead of ? (query) for security
    final_redirect_url = f"{redirect_uri}?token={access_token}"

    # 3. Redirect the browser
    return RedirectResponse(url=final_redirect_url, status_code=status.HTTP_302_FOUND)
# END FIXED SSO LOGIN ENDPOINT

@app.post("/consent/decision")
def consent_decision(
    consent_token: str = Form(...),
    decision: str = Form(...)
):
    pending = get_pending_consent(consent_token)
    if not pending:
        return RedirectResponse(url="/?error=invalid_consent", status_code=status.HTTP_302_FOUND)

    redirect_uri = pending["redirect_uri"]
    app_id = pending["app_id"]
    scopes = normalize_scopes(pending["scopes"])
    user = get_user_by_email(pending["user_email"])
    application = get_application_by_id(app_id)

    if not user or not application:
        delete_pending_consent(consent_token)
        return RedirectResponse(url=f"{redirect_uri}?error=invalid_consent", status_code=status.HTTP_302_FOUND)

    if application.get("blocked"):
        delete_pending_consent(consent_token)
        return RedirectResponse(url=f"{redirect_uri}?error=app_blocked", status_code=status.HTTP_302_FOUND)

    ensure_user_app_access(user["email"], application["id"])
    if is_user_blocked_for_app(user["email"], application["id"]):
        delete_pending_consent(consent_token)
        return RedirectResponse(url=f"{redirect_uri}?error=user_blocked", status_code=status.HTTP_302_FOUND)

    expires_at = datetime.fromisoformat(pending["expires_at"])
    if datetime.utcnow() > expires_at:
        delete_pending_consent(consent_token)
        return RedirectResponse(url=f"{redirect_uri}?error=consent_expired", status_code=status.HTTP_302_FOUND)

    decision_value = decision.lower()
    if decision_value != "approve":
        delete_pending_consent(consent_token)
        return RedirectResponse(url=f"{redirect_uri}?error=access_denied", status_code=status.HTTP_302_FOUND)

    save_user_consent(user["id"], application["id"], scopes)
    delete_pending_consent(consent_token)

    access_token, _ = create_access_token(
        data={
            "sub": user["email"],
            "aud": application["id"],
            "scopes": scopes
        }
    )

    success_redirect = f"{redirect_uri}?token={access_token}"
    return RedirectResponse(url=success_redirect, status_code=status.HTTP_302_FOUND)

@app.post("/oauth/token")
def exchange_authorization_code(payload: OAuthTokenRequest):
    if payload.grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    application = get_application_by_client_id(payload.client_id)
    if not application:
        raise HTTPException(status_code=401, detail="invalid_client")

    if not verify_client_secret_value(payload.client_secret, application.get("client_secret")):
        raise HTTPException(status_code=401, detail="invalid_client")

    if application.get("blocked"):
        raise HTTPException(status_code=403, detail="Application blocked by admin")

    auth_record = consume_authorization_code(payload.code)
    if not auth_record or auth_record["app_id"] != application["id"]:
        raise HTTPException(status_code=400, detail="invalid_grant")

    stored_redirect = auth_record["redirect_uri"]
    if stored_redirect:
        incoming_redirect = payload.redirect_uri or stored_redirect
        if not urls_match(incoming_redirect, stored_redirect):
            raise HTTPException(status_code=400, detail="invalid_redirect")
    elif payload.redirect_uri:
        allowed_redirects = get_allowed_redirects_for_app(application)
        redirect_ok = any(is_redirect_allowed(payload.redirect_uri, allowed) for allowed in allowed_redirects)
        if not redirect_ok:
            raise HTTPException(status_code=400, detail="invalid_redirect")

    user = get_user_by_id(auth_record["user_id"])
    if not user:
        raise HTTPException(status_code=400, detail="invalid_grant")

    if is_user_blocked_for_app(user["email"], application["id"]):
        raise HTTPException(status_code=403, detail="User access blocked by admin")

    scopes = normalize_scopes(auth_record["scopes"]) or DEFAULT_SSO_SCOPES

    access_token, _ = create_access_token(
        data={
            "sub": user["email"],
            "aud": application["id"],
            "scopes": scopes
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "scope": " ".join(scopes)
    }

@app.post("/api/auth/refresh")
def refresh_access_token(token_data: TokenRefresh):
    user_id = verify_refresh_token(token_data.refresh_token)
    
    conn = get_db_connection()
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
        payload = jwt.decode(token_data.token, SECRET_KEY, algorithms=[ALGORITHM], options=JWT_DECODE_OPTIONS)
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
    conn = get_db_connection()
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

# PROFILE MANAGEMENT
@app.put("/api/profile")
def update_profile(profile_data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
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

# API KEY MANAGEMENT
@app.post("/api/keys", response_model=APIKeyResponse)
def create_api_key(key_data: APIKeyCreate, current_user: dict = Depends(get_current_user)):
    key_value = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    
    conn = get_db_connection()
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
    conn = get_db_connection()
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
    conn = get_db_connection()
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

# SDK INTEGRATION ENDPOINTS
@app.post("/api/sdk/login")
def sdk_login(credentials: UserLogin, current_app: dict = Depends(verify_api_key)):
    conn = get_db_connection()
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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options=JWT_DECODE_OPTIONS)
        email = payload.get("sub")
        app_id = payload.get("aud")
        scopes = payload.get("scopes") or DEFAULT_SSO_SCOPES
        if isinstance(scopes, str):
            scopes = normalize_scopes(scopes)

        if not app_id:
            return {"valid": False, "error": "Token missing audience (app) claim"}
        
        user = get_user_by_email(email)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user_has_consent(user["id"], app_id, scopes):
            return {"valid": False, "error": "Required consent not granted"}

        application = get_application_by_id(app_id)
        if not application:
            return {"valid": False, "error": "Application not found"}
        if application.get("blocked"):
            return {"valid": False, "error": "Application blocked by admin"}

        if is_user_blocked_for_app(user["email"], app_id):
            return {"valid": False, "error": "User access blocked by admin"}

        filtered_user = filter_user_data_by_scopes(user, scopes)
        
        return {
            "valid": True,
            "user": filtered_user,
            "scopes": scopes,
            "app_id": app_id
        }
    except JWTError as exc:
        return {"valid": False, "error": str(exc)}

@app.get("/api/sdk/user-profile")
def sdk_user_profile(token: str, current_app: dict = Depends(verify_api_key)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options=JWT_DECODE_OPTIONS)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

    email = payload.get("sub")
    app_id = payload.get("aud")
    scopes = payload.get("scopes") or DEFAULT_SSO_SCOPES
    if isinstance(scopes, str):
        scopes = normalize_scopes(scopes)

    if not email or not app_id:
        raise HTTPException(status_code=400, detail="Token missing required claims")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user_has_consent(user["id"], app_id, scopes):
        raise HTTPException(status_code=403, detail="User has not granted required permissions")

    application = get_application_by_id(app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.get("blocked"):
        raise HTTPException(status_code=403, detail="Application blocked by admin")

    if is_user_blocked_for_app(user["email"], app_id):
        raise HTTPException(status_code=403, detail="User access blocked by admin")

    filtered_user = filter_user_data_by_scopes(user, scopes)
    return {
        "user": filtered_user,
        "app_id": app_id,
        "scopes": scopes
    }

# USER MANAGEMENT
@app.get("/api/users", response_model=List[User])
def get_all_users(current_user: dict = Depends(require_admin)):
    conn = get_db_connection()
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    conn.close()
    
    return {"message": f"Role updated to {role}"}

# APPLICATION MANAGEMENT
@app.post("/api/applications")
def create_application(app_data: ApplicationCreate, current_user: dict = Depends(require_admin)):
    app_id = str(uuid.uuid4())
    normalized_redirect = normalize_redirect_field(app_data.redirect_url)
    client_id_value = app_data.client_id or f"client-{uuid.uuid4().hex[:10]}"
    client_secret_plain = generate_client_secret_value()
    client_secret_hashed = hash_client_secret_value(client_secret_plain)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO applications (id, name, url, client_id, client_secret, redirect_url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        app_id,
        app_data.name,
        app_data.url,
        client_id_value,
        client_secret_hashed,
        normalized_redirect,
    ))
    conn.commit()
    conn.close()
    
    return {
        "id": app_id,
        "name": app_data.name,
        "url": app_data.url,
        "client_id": client_id_value,
        "redirect_url": normalized_redirect,
        "client_secret": client_secret_plain,
        "message": "Application created successfully. Store the client secret securely."
    }

@app.get("/api/applications", response_model=List[Application])
def get_applications(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM applications")
    apps = [dict(row) for row in cursor.fetchall()]
    
    for app in apps:
        app["blocked"] = bool(app.get("blocked", False))
        app["redirect_url"] = serialize_redirect_entries(parse_redirect_entries(app.get("redirect_url")))
        app["client_secret"] = None
        cursor.execute("""
            SELECT user_email, blocked FROM user_app_access 
            WHERE app_id = ?
        """, (app["id"],))
        rows = cursor.fetchall()
        app["authorized_users"] = [{
            "email": row["user_email"],
            "blocked": bool(row["blocked"])
        } for row in rows]
        app["authorized_emails"] = [row["user_email"] for row in rows]
    
    conn.close()
    
    return apps

@app.put("/api/applications/{app_id}")
def update_application(app_id: str, app_data: ApplicationCreate, current_user: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    normalized_redirect = normalize_redirect_field(app_data.redirect_url)
    
    cursor.execute("""
        UPDATE applications 
        SET name = ?, url = ?, client_id = ?, redirect_url = ?
        WHERE id = ?
    """, (
        app_data.name,
        app_data.url,
        app_data.client_id,
        normalized_redirect,
        app_id,
    ))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Application updated successfully"}

@app.post("/api/applications/{app_id}/block")
def set_application_block(app_id: str, payload: ApplicationBlockRequest, current_user: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET blocked = ? WHERE id = ?", (payload.blocked, app_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
    conn.commit()
    conn.close()
    state = "blocked" if payload.blocked else "unblocked"
    return {"message": f"Application {state}"}

@app.post("/api/applications/{app_id}/client-secret", response_model=ClientSecretRotateResponse)
def regenerate_client_secret(app_id: str, current_user: dict = Depends(require_admin)):
    application = get_application_by_id(app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    new_secret = generate_client_secret_value()
    hashed_secret = hash_client_secret_value(new_secret)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET client_secret = ? WHERE id = ?", (hashed_secret, app_id))
    conn.commit()
    conn.close()

    return {
        "app_id": app_id,
        "client_id": application["client_id"],
        "name": application["name"],
        "client_secret": new_secret,
    }

@app.post("/api/applications/{app_id}/users/block")
def set_application_user_block(
    app_id: str,
    payload: ApplicationUserBlockRequest,
    current_user: dict = Depends(require_admin)
):
    application = get_application_by_id(app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (payload.email,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    cursor.execute("""
        SELECT id FROM user_app_access
        WHERE user_email = ? AND app_id = ?
    """, (payload.email, app_id))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
            UPDATE user_app_access
            SET blocked = ?
            WHERE id = ?
        """, (payload.blocked, existing["id"]))
    else:
        cursor.execute("""
            INSERT INTO user_app_access (user_email, app_id, blocked)
            VALUES (?, ?, ?)
        """, (payload.email, app_id, payload.blocked))
    conn.commit()
    conn.close()
    state = "blocked" if payload.blocked else "unblocked"
    return {"message": f"User {payload.email} {state} for this app"}

@app.delete("/api/applications/{app_id}")
def delete_application(app_id: str, current_user: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM user_app_access WHERE app_id = ?", (app_id,))
    cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Application deleted successfully"}

@app.post("/api/applications/{app_id}/api-keys")
def generate_application_api_key(app_id: str, key_data: ApplicationAPIKeyCreate, current_user: dict = Depends(require_admin)):
    app = get_application_by_id(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    key_value = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    key_name = key_data.name or f"{app['name']} Integration Key"

    conn = get_db_connection()
    cursor = conn.cursor()

    # REVOKE ALL PREVIOUS API KEYS FOR THIS APP ---
    cursor.execute("""
        UPDATE api_keys 
        SET revoked = TRUE 
        WHERE app_id = ? AND revoked = FALSE
    """, (app_id,))

    cursor.execute("""
        INSERT INTO api_keys (key_value, user_id, name, app_id)
        VALUES (?, ?, ?, ?)
    """, (key_value, current_user["id"], key_name, app_id))
    conn.commit()
    key_id = cursor.lastrowid
    conn.close()

    return {
        "id": key_id,
        "key_value": key_value,
        "name": key_name,
        "app_id": app_id
    }

@app.get("/api/applications/{app_id}/api-keys")
def list_application_api_keys(app_id: str, current_user: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, created_at, last_used, revoked
        FROM api_keys
        WHERE app_id = ?
        ORDER BY created_at DESC
    """, (app_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.delete("/api/applications/{app_id}/api-keys/{key_id}")
def revoke_application_api_key(app_id: str, key_id: int, current_user: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE api_keys
        SET revoked = TRUE
        WHERE id = ? AND app_id = ?
    """, (key_id, app_id))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="API key not found for this application")

    conn.commit()
    conn.close()

    return {"message": "Application API key revoked"}

# USER-APP MAPPING
@app.post("/api/map")
def map_user_to_app(mapping: MapRequest, current_user: dict = Depends(require_admin)):
    conn = get_db_connection()
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
    conn = get_db_connection()
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT a.* FROM applications a
        INNER JOIN user_app_access uaa ON a.id = uaa.app_id
        WHERE uaa.user_email = ?
    """, (email,))
    
    apps = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return apps

@app.post("/api/user/apps/{app_id}/remove")
def remove_my_app(app_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM applications WHERE id = ?", (app_id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")

    cursor.execute("""
        SELECT id FROM user_app_access
        WHERE user_email = ? AND app_id = ?
    """, (current_user["email"], app_id))
    mapping = cursor.fetchone()
    if not mapping:
        conn.close()
        raise HTTPException(status_code=404, detail="You do not have access to this application")

    cursor.execute("""
        DELETE FROM user_app_access
        WHERE user_email = ? AND app_id = ?
    """, (current_user["email"], app_id))
    conn.commit()
    conn.close()

    log_app_removal(current_user["email"], current_user["name"], app_id, app["name"])

    return {"message": f"Removed access to {app['name']}"}

@app.get("/api/admin/removals")
def get_removal_logs(current_user: dict = Depends(require_admin)):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_email, user_name, app_id, app_name, removed_at
        FROM app_removal_logs
        ORDER BY removed_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    logs = []
    for row in rows:
        entry = dict(row)
        raw_ts = entry.get("removed_at")
        parsed = None
        if isinstance(raw_ts, str):
            try:
                parsed = datetime.fromisoformat(raw_ts)
            except ValueError:
                try:
                    parsed = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    parsed = None
        if parsed:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            entry["removed_at"] = parsed.isoformat()
        logs.append(entry)
    return logs

init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
