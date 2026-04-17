"""First-time Gmail OAuth2 authorization. Run once to generate token.json.
Supports headless/remote environments: if refresh fails, prints URL and
waits for the user to paste the code from the redirect page.
"""
import os
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDS_FILE = Path(__file__).resolve().parents[0] / "credentials.json"
TOKEN_FILE = Path(__file__).resolve().parents[0] / "token.json"


def main():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from requests_oauthlib import OAuth2Session
    import requests

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Step 1: try to use existing token (valid or refreshable)
    if creds and (creds.valid or (creds.expired and creds.refresh_token)):
        if creds.expired and creds.refresh_token:
            print("Token expired, attempting refresh...")
            try:
                creds.refresh(Request())
                TOKEN_FILE.write_text(creds.to_json())
                print(f"Token refreshed and saved to {TOKEN_FILE}")
                _test_connection(creds)
                return
            except Exception as e:
                print(f"Refresh failed: {e}")
                print("Need full re-authorization.")
        elif creds.valid:
            print("Token is still valid.")
            _test_connection(creds)
            return

    # Step 2: full re-authorization via manual code exchange
    print("\n=== Gmail OAuth Re-Authorization Required ===\n")

    # Load client secrets
    import json
    with open(CREDS_FILE) as f:
        client_config = json.load(f)["installed"]

    client_id = client_config["client_id"]
    client_secret = client_config["client_secret"]
    redirect_uri = "http://localhost"

    # Build the session and auth URL
    oauth = OAuth2Session(client_id=client_id, redirect_uri=redirect_uri, scope=SCOPES)
    auth_url, state = oauth.authorization_url(
        "https://accounts.google.com/o/oauth2/auth",
        access_type="offline",
        prompt="consent",
    )

    print("INSTRUCTIONS FOR THE FOUNDER:")
    print("=" * 60)
    print("1. Open the URL below in a web browser on THIS machine")
    print("   (EmpireDell) or a machine with SSH port-forwarding set up.")
    print("")
    print("2. If you're accessing EmpireDell remotely via Cloudflare Tunnel,")
    print("   you MUST set up SSH port forwarding first:")
    print("   ssh -L 8888:localhost:8888 empire@empiredell")
    print("   Then visit http://localhost:8888 in YOUR browser.")
    print("")
    print("   Alternatively, for no-SSH approach:")
    print("   - Visit the URL below from a browser where you can see")
    print("     the address bar after the redirect (even an error page).")
    print("   - After approving, look at the URL in your browser's")
    print("     address bar: http://localhost/?code=XXXXX&state=YYY")
    print("   - Copy the 'code=' value and paste it below.")
    print("")
    print(f"AUTH URL:\n{auth_url}")
    print("=" * 60)
    print("")

    code = input("After approving, paste the 'code=' value from the URL here: ").strip()

    if not code:
        print("No code provided. Exiting.")
        sys.exit(1)

    # Exchange code for tokens
    print("Exchanging code for tokens...")
    try:
        token_url = client_config.get("token_uri", "https://oauth2.googleapis.com/token")
        token_response = requests.post(
            token_url,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_response.raise_for_status()
        token_data = token_response.json()
    except Exception as e:
        print(f"Token exchange failed: {e}")
        sys.exit(1)

    # Build Credentials object and save
    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_url,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    if "expiry" in token_data:
        creds.expiry = token_data["expiry"]

    TOKEN_FILE.write_text(creds.to_json())
    print(f"Token saved to {TOKEN_FILE}")
    _test_connection(creds)


def _test_connection(creds):
    from googleapiclient.discovery import build

    print("Testing connection...")
    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId="me", maxResults=5).execute()
    messages = results.get("messages", [])
    print(f"Success! Found {len(messages)} recent messages.")


if __name__ == "__main__":
    main()
