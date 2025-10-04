from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    token_hash = db.Column(db.String(256), nullable=False)  # store hashed refresh token
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlacklistedToken(db.Model):
    __tablename__ = "token_blacklist"
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(128), nullable=False, unique=True)  # JWT ID
    blacklisted_at = db.Column(db.DateTime, default=datetime.utcnow)

# Optional: if Module 2's app registration table is in same DB, reflect minimal model
class OAuthClient(db.Model):
    __tablename__ = "oauth_clients"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(128), unique=True, nullable=False)
    client_secret_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(256))
    redirect_uris = db.Column(db.Text)  # comma separated or JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
