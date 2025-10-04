from flask_jwt_extended import create_access_token, get_jwt_identity, get_jti
from datetime import datetime, timedelta
from .models import RefreshToken, BlacklistedToken, db
from .utils import hash_token, verify_token_hash, generate_random_token
from flask import current_app

def create_tokens_for_user(user_id: int, identity_payload: dict):
    """
    Returns: (access_token, refresh_token, refresh_expires_at)
    """
    access = create_access_token(identity=identity_payload)
    refresh_plain = generate_random_token()
    # compute expiry
    refresh_expires = datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    refresh_hash = hash_token(refresh_plain)

    r = RefreshToken(user_id=user_id, token_hash=refresh_hash, expires_at=refresh_expires)
    db.session.add(r)
    db.session.commit()
    return access, refresh_plain, refresh_expires

def revoke_access_token_by_jti(jti: str):
    b = BlacklistedToken(jti=jti)
    db.session.add(b)
    db.session.commit()

def is_token_blacklisted(jti: str) -> bool:
    return db.session.query(BlacklistedToken).filter_by(jti=jti).count() > 0

def revoke_refresh_token_by_plain(token_plain: str):
    # Find matching hashed token and delete (or mark expired)
    rows = db.session.query(RefreshToken).all()
    for r in rows:
        try:
            if verify_token_hash(token_plain, r.token_hash):
                db.session.delete(r)
                db.session.commit()
                return True
        except Exception:
            continue
    return False

def verify_and_consume_refresh_token(token_plain: str):
    """
    Verify refresh token exists and not expired.
    Optionally consume or rotate the refresh token.
    Returns user_id if valid else None.
    """
    tokens = db.session.query(RefreshToken).filter(RefreshToken.expires_at > datetime.utcnow()).all()
    for t in tokens:
        try:
            if verify_token_hash(token_plain, t.token_hash):
                # Optionally rotate: delete old token and create a new one (recommended)
                user_id = t.user_id
                db.session.delete(t)
                db.session.commit()
                return user_id
        except Exception:
            continue
    return None
