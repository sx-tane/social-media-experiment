import webbrowser
import hashlib
import base64
import os
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# This script will now load your credentials from your .env file.
# Make sure TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET are set in that file.
CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")

# This MUST match the redirect URI in your TikTok app's configuration
REDIRECT_URI = "https://www.tourii.xyz/auth/callback"
# The scopes your app requires.
SCOPES = ["user.info.basic", "video.publish"]

def get_access_token(code, code_verifier):
    """Exchanges the authorization code for an access token."""
    print("\n🔄 Exchanging authorization code for an access token...")
    
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {
        'client_key': CLIENT_KEY,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
        'code_verifier': code_verifier,
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        token_data = response.json()
        
        print("\n✨ --- SUCCESS! Your Tokens Are Ready --- ✨")
        print(f"\nAccess Token: \n{token_data.get('access_token')}")
        print(f"\nOpen ID: \n{token_data.get('open_id')}")
        print(f"\nRefresh Token: \n{token_data.get('refresh_token')}")
        print(f"\nScope: {token_data.get('scope')}")
        print(f"\nExpires In: {token_data.get('expires_in')} seconds")
        print("\n📋 Copy the TIKTOK_REFRESH_TOKEN value and add it to your .env file.")
        
    except requests.exceptions.RequestException as e:
        print("\n❌ An error occurred while fetching the access token.")
        print(f"Status Code: {e.response.status_code}")
        print(f"Response: {e.response.text}")

def main():
    print("--- TikTok OAuth 2.0 Token Generator (Manual Flow) ---")

    if not CLIENT_KEY or not CLIENT_SECRET:
        print("\n❗️ Error: Your TIKTOK_CLIENT_KEY or TIKTOK_CLIENT_SECRET is not set.")
        print("   Please check your '.env' file and make sure it contains your credentials.")
        return

    # 1. Generate Code Verifier, Challenge, and State for PKCE
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('utf-8')
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).rstrip(b'=').decode('utf-8')
    state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b'=').decode('utf-8')

    # 2. Construct the Authorization URL
    scope_string = ",".join(SCOPES)
    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize?"
        f"client_key={CLIENT_KEY}&"
        f"scope={scope_string}&"
        f"response_type=code&"
        f"redirect_uri={REDIRECT_URI}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256&"
        f"state={state}"
    )

    # 3. Prompt user to open the URL
    print("\n--- Step 1: Authorize Application ---")
    print("\n👉 Please open the following URL in your browser (it should open automatically):")
    print(f"\n{auth_url}")
    webbrowser.open(auth_url)

    # 4. Prompt user to paste the redirect URL
    print("\n--- Step 2: Paste the Redirect URL ---")
    print("\nAfter authorizing, your browser will be redirected to a URL that starts with 'https://www.tourii.xyz/auth/callback...'.")
    print("📋 Please copy the FULL URL from your browser's address bar and paste it here:")
    redirect_url = input("\nEnter the full redirect URL: ")

    # 5. Parse the code and state from the pasted URL
    try:
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        
        authorization_code = query_params.get("code", [None])[0]
        returned_state = query_params.get("state", [None])[0]

        if not authorization_code:
            print("\n❌ Error: Could not find 'code' in the URL you pasted. Please try again.")
            return

        if returned_state != state:
            print("\n❌ Error: State parameter mismatch. This is a security risk. Please try again.")
            return

        print("\n✅ Authorization code received successfully.")
        get_access_token(authorization_code, code_verifier)

    except Exception as e:
        print(f"\n❌ An error occurred while parsing the URL: {e}")
        print("   Please make sure you pasted the full and correct URL.")

if __name__ == "__main__":
    main() 