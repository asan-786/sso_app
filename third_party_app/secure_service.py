from flask import Flask, request, jsonify, redirect, url_for
from flask_cors import CORS
import json
import os
import sys

# --- 1. SETUP PATH TO IMPORT SSO_PY_SDK.py ---
# This assumes your project structure includes an SDK directory.
# This line is crucial for finding the SDK module.
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'sdk'))
# from SSO_PY_SDK import SSOClient, SSOServiceError 

# NOTE: Since the SSO_PY_SDK is not available in this environment, 
# we'll simulate the SSOClient's verification step for demonstration.
# In a real environment, you MUST uncomment the lines above and ensure 
# the SDK is correctly imported.

# Placeholder for simulated user data from token verification
# In a real app, this would be the actual data verified by the SDK
SSO_USER_DATA_SIMULATION = {
    "id": "user-sso-12345",
    "name": "Alex Doe",
    "email": "alex.doe@campus.edu",
    "role": "student"
}

class SSOServiceError(Exception):
    """Simulated exception for SSO failure."""
    pass

class SSOClient:
    """Simulated SSO Client for demonstration purposes."""
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("API key must be provided.")
        print("SSO Client (Simulated) initialized successfully.")
    
    def verify_token(self, token):
        """Simulates successful token verification for any non-empty token."""
        if not token or token == "invalid_token":
            raise SSOServiceError("Token is invalid or expired.")
        
        # In a real scenario, the SDK would fetch and verify the JWT 
        # against the main SSO server and return real user data.
        return SSO_USER_DATA_SIMULATION

# --- 2. CONFIGURATION ---
app = Flask(__name__)
CORS(app) # Allow CORS for frontend running on a different port/origin

# !!! REPLACE WITH YOUR ACTUAL API KEY FROM SSO DASHBOARD !!!
APP_API_KEY = "sso_live_Lw_MaaLm92aRjGLa-CunEZWMovqo-_QpuZdMXiryaMk" 

try:
    sso_client = SSOClient(api_key=APP_API_KEY)
    sso_client_ready = True
except ValueError as e:
    print(f"ERROR: Failed to initialize SSO Client: {e}")
    sso_client_ready = False

# --- 3. MIDDLEWARE / PROTECTION FUNCTION ---
def require_sso_token():
    """Custom decorator/function to verify the JWT token using the Python SDK (simulated)."""
    if not sso_client_ready:
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
        "access_granted_to": sso_user['email'],
        "resource_details": {
            "title": "Secret University Records",
            "content": f"User {sso_user['name']} with ID {sso_user['id']} has successfully accessed protected resource.",
            "policy_applied": "SSO Token Verification"
        }
    })

# NOTE: This endpoint is not directly used for token exchange, but is included 
# to show how a backend might handle a redirect if the SSO server directly 
# redirects with a code or token to a non-frontend URL. 
# In this specific front-end implementation, the front-end handles the token extraction 
# from the hash and immediately uses it with /secure-data.
@app.route("/sso-success")
def sso_success():
    """Placeholder for the SSO success redirect if handled by the backend."""
    token = request.args.get('token')
    
    if token:
        # Since the frontend is handling the token extraction from the hash, 
        # this path is mainly informational for the backend setup.
        return jsonify({"message": "Token received by server (not used by this client-side flow).", "token_length": len(token)}), 200
    
    return jsonify({"message": "No token provided in query params."}), 400


if __name__ == "__main__":
    # NOTE: Run this Flask app on a different port (8080) than your FastAPI SSO backend (3000)
    print("Starting Third-Party Resource Server on http://127.0.0.1:8080")
    print("Ensure main SSO backend is running on http://localhost:3000")
    app.run(host="0.0.0.0", port=8080)
