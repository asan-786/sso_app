from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, create_access_token
from .token_service import create_tokens_for_user, revoke_access_token_by_jti, is_token_blacklisted, verify_and_consume_refresh_token, revoke_refresh_token_by_plain
from .models import db
import datetime

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# ---------- Helper: adapt to Module 1 ---------- #
def verify_user_credentials(username: str, password: str):
    """
    Verify credentials against Module 1 user DB or API.
    Return user dict on success: {'id': 123, 'username': 'aryan', 'role': 'student', 'email': '...'}
    Return None on failure.
    TODO/ADAPT: Replace this with the actual call to Module 1 or shared DB model.
    """
    # Example stub for local testing (remove in production)
    if username == "test" and password == "testpass":
        return {"id": 1, "username": "test", "role": "student", "email": "test@example.com"}
    # If Module1 exposes HTTP API:
    # r = requests.post(f"{USER_SVC_URL}/users/verify", json={...}) 
    # if r.ok: return r.json()
    return None

# -------- Login endpoint --------
@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"msg": "username and password required"}), 400

    user = verify_user_credentials(username, password)
    if not user:
        return jsonify({"msg": "invalid credentials"}), 401

    identity_payload = {"sub": user["id"], "username": user["username"], "role": user.get("role", "student")}
    access, refresh_plain, refresh_expires = create_tokens_for_user(user_id=user["id"], identity_payload=identity_payload)

    return jsonify({
        "access_token": access,
        "refresh_token": refresh_plain,
        "expires_in": int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()),
        "refresh_expires_at": refresh_expires.isoformat()
    }), 200

# -------- Refresh endpoint --------
@bp.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json() or {}
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        return jsonify({"msg": "refresh_token required"}), 400

    user_id = verify_and_consume_refresh_token(refresh_token)
    if not user_id:
        return jsonify({"msg": "invalid or expired refresh token"}), 401

    # Fetch user info (adapt)
    # TODO: Replace with Module1 DB lookup / API call
    user = {"id": user_id, "username": f"user{user_id}", "role": "student"}

    new_access = create_access_token(identity={"sub": user["id"], "username": user["username"], "role": user["role"]})
    # Optionally issue a new refresh token (rotation)
    return jsonify({
        "access_token": new_access,
        "expires_in": int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
    }), 200

# -------- Logout --------
@bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    claims = get_jwt()
    jti = claims.get("jti")
    if not jti:
        return jsonify({"msg": "invalid token supplied"}), 400
    revoke_access_token_by_jti(jti)
    # Consume refresh token if provided
    data = request.get_json() or {}
    refresh_token = data.get("refresh_token")
    if refresh_token:
        revoke_refresh_token_by_plain(refresh_token)
    return jsonify({"msg": "successfully logged out"}), 200

# -------- Verify token --------
@bp.route("/verify", methods=["GET"])
@jwt_required()
def verify():
    claims = get_jwt()
    jti = claims.get("jti")
    if is_token_blacklisted(jti):
        return jsonify({"msg": "token revoked"}), 401
    return jsonify({"valid": True, "claims": claims}), 200
