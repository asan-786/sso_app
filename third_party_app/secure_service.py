from flask import Flask, request, jsonify, redirect, url_for
from flask_cors import CORS
import json
import os
import sys

# --- 1. SETUP PATH TO IMPORT SSO_PY_SDK.py ---
# This adjusts the path so we can import the SDK file
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'sdk'))
from SSO_PY_SDK import SSOClient, SSOServiceError  # noqa: E402

# --- 2. CONFIGURATION ---
app = Flask(__name__)
CORS(app) # Allow CORS for frontend running on a different port/origin

# MANDATORY CHANGE: Load API Key from environment variable 
# This key is used to authenticate this app with the SSO backend for /sdk endpoints.
APP_API_KEY = os.getenv(
    "CAMPUSCONNECT_API_KEY", 
    "sso_live_cc_demo_primary_4d2d59" # Fallback for local testing/seeding
)

if not APP_API_KEY or APP_API_KEY == "sso_live_cc_demo_primary_4d2d59":
    print("WARNING: Using default/demo CAMPUSCONNECT_API_KEY. Rotate this for production!")

try:
    sso_client = SSOClient(api_key=APP_API_KEY)
    sso_client_ready = True
except ValueError as e:
    print(f"ERROR: Failed to initialize SSO Client: {e}")
    sso_client_ready = False

# --- 3. MIDDLEWARE / PROTECTION FUNCTION ---
def require_sso_token():
    """Custom function to verify the JWT token using the Python SDK."""
    if not sso_client_ready:
        return {"message": "SSO Service is not configured on this server."}, 500

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return {"message": "Authorization header missing or invalid"}, 401
    
    token = auth_header.split(" ")[1]

    try:
        # CORE STEP: Verify the token and get the filtered user profile in one go
        verification = sso_client.verify_token(token)
        profile = sso_client.get_user_profile(token)

        # Combine user info: 'profile' (rich data filtered by scopes) is primary, 
        # 'verification' (minimal data) is fallback/sanity check
        v_user = verification.get("user") or {}
        p_user = profile.get("user") or {}
        
        # Merge, giving preference to the detailed 'profile' data
        combined_user = {**v_user, **p_user}

        # Ensure academic fields exist, even if not shared, for consistent UI display
        combined_user.setdefault("rollNo", combined_user.get("roll_no", "Not shared"))
        combined_user.setdefault("branch", combined_user.get("branch", "Not shared"))
        combined_user.setdefault("semester", combined_user.get("semester", "Not shared"))

        # Store verified data in request context (Flask trick to pass data to routes)
        request.sso_verification = verification
        request.sso_user = combined_user
        request.sso_scopes = profile.get("scopes", verification.get("scopes", []))
        request.sso_app_id = profile.get("app_id", verification.get("app_id"))
        
        return None # No error, continue with the request
        
    except SSOServiceError as e:
        print(f"Token Verification Failed: {e}")
        return {"message": "Invalid or expired SSO token. Please re-login.", "error": str(e)}, 401


# --- 4. APPLICATION ROUTES ---

@app.route("/")
def index():
    """Simple health check for the demo server."""
    return jsonify({"status": "Third-Party Server Running", "sso_client_ready": bool(sso_client_ready)})

@app.route("/secure-data")
def secure_data():
    """
    A protected endpoint that first verifies the SSO token before granting access.
    The frontend calls this immediately after successful SSO redirect.
    """
    # Run the token verification logic
    error_response = require_sso_token()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    # Access is granted! Use the user data verified by the SSO server
    sso_user = request.sso_user
    
    # Return the secure, protected data
    return jsonify({
        "message": "Access granted.",
        "access_granted_to": sso_user.get('email'),
        "granted_scopes": request.sso_scopes,
        "app_id": request.sso_app_id,
        "user": sso_user,
        "resource_details": {
            "title": "Secret University Records",
            "content": f"User {sso_user.get('name')} with ID {sso_user.get('id')} has successfully accessed protected resource.",
            "policy_applied": "SSO Token Verification"
        }
    })

@app.route("/sso-success")
def sso_success():
    """Placeholder for the SSO success redirect if handled by the backend."""
    token = request.args.get('token')
    
    if token:
        return jsonify({"message": "Token received by server (not used by this client-side flow).", "token_length": len(token)}), 200
    
    return jsonify({"message": "No token provided in query params."}), 400


if __name__ == "__main__":
    # NOTE: Run this Flask app on a different port (8080) than your FastAPI SSO backend (8000)
    print("Starting Third-Party Resource Server on http://127.0.0.1:8080")
    print("Ensure main SSO backend is running on http://127.0.0.1:8000")
    app.run(host="0.0.0.0", port=8080)