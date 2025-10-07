import requests
import json
from typing import Optional, Dict, Any

class SSOServiceError(Exception):
    """Custom exception for SSO service errors."""
    pass

class SSOClient:
    """
    Python SDK for Enterprise SSO Integration.

    Used by third-party application backends (Resource Servers) to securely
    verify tokens and authenticate users against the SSO portal.
    """
    API_URL = "http://127.0.0.1:8000/api"

    def __init__(self, api_key: str):
        """
        Initialize the client with the application's API Key.
        :param api_key: The Developer API Key generated in the SSO portal.
        """
        if not api_key:
            raise ValueError("API Key is required for SSOClient initialization.")
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticates a user and retrieves an access token.
        This is typically used in the backend to facilitate the token retrieval.
        
        :param email: User's email.
        :param password: User's password.
        :return: A dictionary containing the token and user details.
        :raises SSOServiceError: If login fails.
        """
        endpoint = f"{self.API_URL}/sdk/login"
        payload = {"email": email, "password": password}
        
        try:
            response = requests.post(endpoint, headers=self.headers, data=json.dumps(payload))
            data = response.json()
            
            if response.status_code != 200:
                raise SSOServiceError(data.get("detail", "SSO Login Failed"))
            
            return data
            
        except requests.RequestException as e:
            raise SSOServiceError(f"Network error: {e}")

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verifies the validity of an access token and retrieves the user's information.
        This is the most critical function for securing resource server endpoints.
        
        :param token: The JWT access token received from the client.
        :return: A dictionary containing the validated user object.
        :raises SSOServiceError: If the token is invalid or expired.
        """
        endpoint = f"{self.API_URL}/sdk/verify?token={token}"
        
        try:
            # We use GET here as the backend is configured to accept the token as a query parameter
            response = requests.get(endpoint, headers=self.headers)
            data = response.json()
            
            if response.status_code != 200 or not data.get("valid"):
                raise SSOServiceError(data.get("detail", "Token validation failed"))
            
            return data["user"] # Returns the validated user object
            
        except requests.RequestException as e:
            raise SSOServiceError(f"Network error: {e}")

# Example usage (for documentation purposes, not part of the class)
"""
if __name__ == '__main__':
    # Replace with an actual API key generated from the SSO Admin Dashboard
    APP_API_KEY = "sso_live_YOUR_GENERATED_API_KEY" 
    
    try:
        sso_client = SSOClient(api_key=APP_API_KEY)
        
        # 1. Login to get a token (usually done by the client/frontend)
        auth_response = sso_client.login("student@example.com", "student123")
        access_token = auth_response['access_token']
        print(f"Login successful. Access Token: {access_token[:10]}...")
        
        # 2. Verify the token (done by the Resource Server/Backend)
        user_data = sso_client.verify_token(access_token)
        print("\nToken Verification Successful:")
        print(json.dumps(user_data, indent=2))
        
    except SSOServiceError as e:
        print(f"SSO Error: {e}")
    except ValueError as e:
        print(f"Configuration Error: {e}")
"""
