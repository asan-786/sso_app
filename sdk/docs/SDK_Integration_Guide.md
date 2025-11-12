SSO Portal Integration Guide (Module 4)
This guide provides the necessary information and code snippets for third-party application developers to integrate with the Enterprise Single Sign-On (SSO) Service.

Prerequisites
Application Registration: Your application must be registered in the SSO Admin Dashboard (Manage Applications tab). Each application must have a `client_id`. This identifier is required when sending users to the hosted SSO login page so that the backend can map the login to your app and enforce consent.

User Consent: During the hosted login flow, the SSO service will automatically prompt users to grant the scopes you request (for example, `profile`, `email`, or `student_academics` for roll number / branch / semester access). Tokens issued for third-party apps include the granted scopes and the target application (`aud` claim).

API Key: You must generate a Developer API Key from the student dashboard's Developer API Keys section. This key is used to authenticate your application itself with the SSO Service when calling `/api/sdk/*` endpoints.

JavaScript Client SDK (Frontend Applications)
Use this SDK for applications built with frameworks like React, Vue, or plain HTML/JS to handle user login and token management.

Installation & Setup
Since we are not creating an NPM package, you can simply include the SSOService class in your project.

// sdk/SSO_JS_SDK.js (or copy/paste the class content)
// Initialize the service with your application's API Key
const YOUR_APP_API_KEY = "sso_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"; // Replace with your generated key
const ssoService = new SSOService(YOUR_APP_API_KEY);

Core Functions
1. Login and Token Retrieval (loginWithSSO)
This function initiates the authentication flow.

// Example: Handling a login form submission
async function handleSSOLogin(email, password) {
    const result = await ssoService.loginWithSSO(email, password);

    if (result.success) {
        console.log("Login successful! User:", result.user.name);
        // Redirect user to the main app page
        window.location.href = '/dashboard';
    } else {
        console.error("Login failed:", result.message);
        // Show error message to the user
    }
}

2. Access Token Management (getAccessToken)
Retrieve the currently active JWT access token stored on the client.

const token = ssoService.getAccessToken();

if (token) {
    // Use the token for secure requests to your own Resource Server
    // Example: fetch('/api/resource', { headers: { 'Authorization': `Bearer ${token}` } })
}

3. Client-side Token Validation (verifyToken)
Use this to verify if the locally held token is still valid with the SSO service (e.g., on page load).

async function checkSession() {
    const token = ssoService.getAccessToken();
    if (!token) return;

    const validation = await ssoService.verifyToken(token);

    if (validation.valid) {
        console.log("Session is valid. Granted scopes:", validation.scopes);
    } else {
        console.log("Session expired. Please log in again.");
        ssoService.logout(); // Clear the expired local token
    }
}

4. Fetching Scoped Profile Data (fetchUserProfile)
Once the user has granted consent, you can retrieve the approved profile fields:

const token = ssoService.getAccessToken();
const profileResult = await ssoService.fetchUserProfile(token);

if (profileResult.success) {
    console.log("User profile:", profileResult.profile);
} else {
    console.error("Failed to load user profile:", profileResult.message);
}
sso_client = SSOClient(api_key=YOUR_APP_API_KEY)

Python Server SDK (Backend Applications)
Use this SDK for securing your backend services (Resource Servers) built with Python (e.g., Flask, Django, FastAPI). The primary use case is token verification.

Installation & Setup
This SDK requires the requests library (pip install requests).

# Save the provided SSO_PY_SDK.py file
from SSO_PY_SDK import SSOClient, SSOServiceError

YOUR_APP_API_KEY = "sso_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" # Replace with your generated key
sso_client = SSOClient(api_key=YOUR_APP_API_KEY)

Core Function: Secure Resource Endpoints
The core function is verify_token(), which should be integrated into your application's middleware or route protection logic.

# Example integration in a Flask/FastAPI backend framework:

def protected_route_handler(request):
    # 1. Get the token from the Authorization header (e.g., Bearer token)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return {"error": "Authentication header missing"}, 401
    
    token = auth_header.split(" ")[1]

    try:
        # 2. Verify the token with the SSO service
        verification = sso_client.verify_token(token)

        # 3. Retrieve the consented user profile
        profile = sso_client.get_user_profile(token)
        
        # 4. If successful, grant access and use user data
        return {
            "message": "Access granted",
            "user": profile["user"],
            "scopes": profile["scopes"],
            "app_id": profile["app_id"]
        }, 200
        
    except SSOServiceError as e:
        # 5. If verification fails (e.g., token expired), deny access
        return {"error": str(e), "message": "Invalid token"}, 401
