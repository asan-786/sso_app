import sqlite3
import os
import inspect

# --- 1. Define the correct DB Path (same as before) ---
DB_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    "sso_database.db"
)

# --- 2. Define the Target Redirect URLs ---

# CampusConnect Demo (App 1): Runs on 5501
REDIRECTS_APP1 = """
http://127.0.0.1:5501/third_party_app/index.html
http://127.0.0.1:5501/sso_app/third_party_app/index.html
"""

# CampusConnect Plus Demo (App 2): Must run on 5500 and accept the hash fragment
REDIRECTS_APP2 = """
http://127.0.0.1:5500/index2.html#/sso-success
http://127.0.0.1:5500/third_party_app_2/index2.html
http://127.0.0.1:5500/sso_app/third_party_app_2/index2.html
"""

def update_all_redirect_urls():
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        cursor = conn.cursor()
        
        print(f"Connecting to database at: {DB_FILE_PATH}")
        
        # --- UPDATE APP 1 (CampusConnect Demo) to 5501 ---
        cursor.execute("""
            UPDATE applications
            SET redirect_url = ?
            WHERE client_id = ?
        """, (REDIRECTS_APP1.strip(), "campusconnect-client"))
        print(f"App 1 (5501) updated. Rows changed: {cursor.rowcount}")

        # --- UPDATE APP 2 (CampusConnect Plus Demo) to 5500 ---
        cursor.execute("""
            UPDATE applications
            SET redirect_url = ?
            WHERE client_id = ?
        """, (REDIRECTS_APP2.strip(), "campusconnect-client-2"))
        print(f"App 2 (5500) updated. Rows changed: {cursor.rowcount}")

        conn.commit()
        print("SUCCESS: Database configuration committed.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_all_redirect_urls()