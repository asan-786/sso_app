from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import sys

# --- 1. SETUP PATH TO IMPORT SSO_PY_SDK.py ---
# This assumes your project structure is:
# project-root/
# ├── sdk/
# │   └── SSO_PY_SDK.py
# └── third_party_app/
#     └── secure_service.py
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'sdk'))
from SSO_PY_SDK import SSOClient, SSOServiceError 

# --- 2. CONFIGURATION ---
app = Flask(__name__)
CORS(app) # Allow CORS for frontend running on a different port/origin

# !!! REPLACE WITH YOUR ACTUAL API KEY FROM SSO DASHBOARD !!!
# This key is REQUIRED for the Python SDK to communicate with the SSO main server.
APP_API_KEY = "sso_live_Lw_MaaLm92aRjGLa-CunEZWMovqo-_QpuZdMXiryaMk" 

try:
    sso_client = SSOClient(api_key=APP_API_KEY)
    print("SSO Client initialized successfully.")
except ValueError as e:
    print(f"ERROR: Failed to initialize SSO Client: {e}")
    sso_client = None

# --- 3. MIDDLEWARE / PROTECTION FUNCTION ---
def require_sso_token():
    """Custom decorator/function to verify the JWT token using the Python SDK."""
    if not sso_client:
        return {"message": "SSO Service is not configured on this server."}, 500

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return {"message": "Authorization header missing or invalid"}, 401
    
    token = auth_header.split(" ")[1]

    try:
        # **CORE STEP: Use the Python SDK to verify the token with the SSO server**
        user_data = sso_client.verify_token(token)
        
        # If verification is successful, store user data in request context
        request.sso_user = user_data 
        return None # No error, continue with the request
        
    except SSOServiceError as e:
        print(f"Token Verification Failed: {e}")
        return {"message": "Invalid or expired SSO token. Please re-login.", "error": str(e)}, 401

# --- 4. APPLICATION ROUTES ---
@app.route("/")
def index():
    """Simple health check for the demo server."""
    return jsonify({"status": "Third-Party Server Running", "sso_client_ready": bool(sso_client)})

@app.route("/secure-data")
def secure_data():
    """
    A protected endpoint that first verifies the SSO token before granting access.
    """
    # Run the token verification logic
    error_response = require_sso_token()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    # Access is granted! Use the user data verified by the SSO server
    sso_user = request.sso_user
    
    # Return the secure, protected data
    return jsonify({
        "message": "Welcome! This is highly protected data.",
        "access_granted_to": sso_user['email'],
        "resource_details": {
            "title": "Secret University Records",
            "content": f"User {sso_user['name']} with ID {sso_user['id']} has successfully accessed protected resource.",
            "policy_applied": "SSO Token Verification"
        }
    })

if __name__ == "__main__":
    # NOTE: Run this Flask app on a different port (8080) than your FastAPI SSO backend (8000)
    print("Starting Third-Party Resource Server on http://127.0.0.1:8080")
    print("Ensure main SSO backend is running on http://127.0.0.1:8000")
    app.run(host="0.0.0.0", port=8080)
