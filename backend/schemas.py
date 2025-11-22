from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Tuple

# PYDANTIC MODELS
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
    redirect_url: Optional[str] = ""

class ApplicationAuthorizedUser(BaseModel):
    email: EmailStr
    blocked: bool = False

class Application(BaseModel):
    id: str
    name: str
    url: str
    client_id: Optional[str] = ""
    redirect_url: Optional[str] = ""
    blocked: bool = False
    authorized_emails: List[str] = Field(default_factory=list)
    authorized_users: List[ApplicationAuthorizedUser] = Field(default_factory=list)

class ClientSecretRotateResponse(BaseModel):
    app_id: str
    client_id: str
    name: str
    client_secret: str

class OAuthTokenRequest(BaseModel):
    grant_type: str = "authorization_code"
    code: str
    redirect_uri: Optional[str] = None
    client_id: str
    client_secret: str

class ApplicationBlockRequest(BaseModel):
    blocked: bool

class ApplicationUserBlockRequest(BaseModel):
    email: EmailStr
    blocked: bool

class MapRequest(BaseModel):
    email: str
    app_id: str

class ApplicationAPIKeyCreate(BaseModel):
    name: Optional[str] = None

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

class UserInDB(User):
    """Schema used for retrieving user data from the DB, includes the hash."""
    password_hash: str