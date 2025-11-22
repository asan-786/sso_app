import os
from typing import List, Tuple

# CORE CONFIGURATION
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

# Token Expiry
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30
AUTH_CODE_EXPIRY_MINUTES = 5

# API Keys and Secrets
API_KEY_PREFIX = "sso_live_"
CLIENT_SECRET_BYTES = 32

# Frontend URLs (Used for redirects)
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
FRONTEND_REGISTER_URL = os.getenv("FRONTEND_REGISTER_URL", f"{FRONTEND_BASE_URL}?view=register")

# SSO & SCOPE CONFIGURATION
SCOPE_FIELD_MAP = {
    "profile": ["name"],
    "email": ["email"],
    "student_academics": ["roll_no", "branch", "semester"],
    "role": ["role"]
}
DEFAULT_SSO_SCOPES = ["profile", "email", "student_academics"]

# Used by init_db to store generated secrets for seeded apps
seeded_client_secrets: List[Tuple[str, str, str]] = []