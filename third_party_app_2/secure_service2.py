from flask import Flask, request, jsonify, redirect, url_for
from flask_cors import CORS
import json
import os
import sys

# --- 1. SETUP PATH TO IMPORT SSO_PY_SDK.py ---
# Ensures we can import the custom Python SDK
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'sdk'))
from SSO_PY_SDK import SSOClient, SSOServiceError  # noqa: E402

# --- 2. CONFIGURATION ---
app = Flask(__name__)
CORS(app)  # Allow CORS for frontend running on a different port/origin

# MANDATORY CHANGE: Load API Key from environment variable (Best Practice)
# The key is dedicated to CampusConnect Plus Demo (auto-seeded)
APP_API_KEY = os.getenv(
    "CAMPUSCONNECT_PLUS_API_KEY", 
    "sso_live_cc_plus_primary_a13b78" # Fallback for local testing/seeding
)

if not APP_API_KEY or APP_API_KEY == "sso_live_cc_plus_primary_a13b78":
    print("WARNING: Using default/demo CAMPUSCONNECT_PLUS_API_KEY. Rotate this for production!")

try:
    sso_client = SSOClient(api_key=APP_API_KEY)
    sso_client_ready = True
except ValueError as e:
    print(f"ERROR: Failed to initialize SSO Client for App 2: {e}")
    sso_client_ready = False

# --- 3. MIDDLEWARE / PROTECTION FUNCTION ---
def require_sso_token():
    """Verify the JWT token using the Python SDK for this second app."""
    if not sso_client_ready:
        return {"message": "SSO Service is not configured on this server."}, 500

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return {"message": "Authorization header missing or invalid"}, 401

    token = auth_header.split(" ")[1]

    try:
        # Use the SDK to verify and get filtered profile
        verification = sso_client.verify_token(token)
        profile = sso_client.get_user_profile(token)

        v_user = verification.get("user") or {}
        p_user = profile.get("user") or {}
        combined_user = {**v_user, **p_user}

        # Ensure academic fields exist
        combined_user.setdefault("rollNo", combined_user.get("roll_no", "Not shared"))
        combined_user.setdefault("branch", combined_user.get("branch", "Not shared"))
        combined_user.setdefault("semester", combined_user.get("semester", "Not shared"))

        request.sso_verification = verification
        request.sso_user = combined_user
        request.sso_scopes = profile.get("scopes", verification.get("scopes", []))
        request.sso_app_id = profile.get("app_id", verification.get("app_id"))
        return None

    except SSOServiceError as e:
        print(f"[App2] Token Verification Failed: {e}")
        return {"message": "Invalid or expired SSO token. Please re-login.", "error": str(e)}, 401


@app.route("/")
def index():
    """Health check for the second demo server."""
    return jsonify({"status": "Third-Party Server 2 Running", "sso_client_ready": bool(sso_client_ready)})


@app.route("/secure-data")
def secure_data():
    """Protected endpoint for the second app."""
    error_response = require_sso_token()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    sso_user = request.sso_user

    return jsonify(
        {
            "message": "Access granted from App 2.",
            "access_granted_to": sso_user.get("email"),
            "granted_scopes": request.sso_scopes,
            "app_id": request.sso_app_id,
            "user": sso_user,
            "resource_details": {
                "title": "Second App Secret Records",
                "content": f"[App2] User {sso_user.get('name')} ({sso_user.get('email')}) accessed secondary resource.",
                "policy_applied": "SSO Token Verification (App 2)",
            },
        }
    )

@app.route("/sso-success")
def sso_success():
    """Placeholder for the SSO success redirect if handled by the backend."""
    token = request.args.get('token')
    
    if token:
        return jsonify({"message": "Token received by server (not used by this client-side flow).", "token_length": len(token)}), 200
    
    return jsonify({"message": "No token provided in query params."}), 400

if __name__ == "__main__":
    print("Starting Second Third-Party Resource Server on http://127.0.0.1:8081")
    print("Ensure main SSO backend is running on http://127.0.0.1:8000")
    app.run(host="0.0.0.0", port=8081)