import sqlite3
import os
import inspect
from typing import List, Tuple, Optional
# ... other imports ...

# Define the correct DB Path 
DB_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    "sso_database.db"
)

# --- Define the New Redirect URLs to include the dynamic ports ---
# Since the frontend generates the URL with the hash fragment, we must register 
# the expected full URL to ensure the SSO backend accepts it.
NEW_REDIRECT_URLS = """
http://127.0.0.1:5500/index2.html#/sso-success
http://127.0.0.1:5501/index2.html#/sso-success
http://127.0.0.1:5502/index2.html#/sso-success

# Also include the base redirect paths from the original seed data for robustness
http://127.0.0.1:5500/third_party_app_2/index2.html
http://127.0.0.1:5501/third_party_app_2/index2.html
http://127.0.0.1:5502/third_party_app_2/index2.html
"""

# --- Update Function ---
def update_redirect_urls():
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        cursor = conn.cursor()

        CLIENT_ID = "campusconnect-client-2"
        
        print(f"Updating redirect URLs for client: {CLIENT_ID}...")

        # Get the serialized redirect list (using comma/newline separation)
        # Note: We are using NEW_REDIRECT_URLS.strip() which is a clean newline-separated list
        
        # Execute the update command
        cursor.execute("""
            UPDATE applications
            SET redirect_url = ?
            WHERE client_id = ?
        """, (NEW_REDIRECT_URLS.strip(), CLIENT_ID))

        if cursor.rowcount > 0:
            print(f"SUCCESS: {cursor.rowcount} application record(s) updated.")
            conn.commit()
        else:
            print("WARNING: No application found with that client_id. Database may be empty.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_redirect_urls()