"""Google Drive READ-ONLY authorization for Max's file finder (drive.readonly).

Uses the same Google OAuth client as Gmail (~/.config/empirebox/gmail/credentials.json)
and saves a separate token at ~/.config/empirebox/gdrive/token.json. The rclone
"gdrive" remote has full read-write scope and is not used by Max.

  venv/bin/python drive_auth.py --browser   # at the Dell: opens Google sign-in, one click
  venv/bin/python drive_auth.py             # anywhere: prints a URL, paste back the code
"""
import json
import os
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_GMAIL_DIR = Path.home() / ".config" / "empirebox" / "gmail"
CREDS_FILE = Path(os.environ.get("GDRIVE_CREDENTIALS_PATH") or os.environ.get("GMAIL_CREDENTIALS_PATH")
                  or (_GMAIL_DIR / "credentials.json"))
TOKEN_FILE = Path(os.environ.get("GDRIVE_TOKEN_PATH") or (Path.home() / ".config" / "empirebox" / "gdrive" / "token.json"))


def _save(creds):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(TOKEN_FILE.parent, 0o700)
    TOKEN_FILE.write_text(creds.to_json())
    os.chmod(TOKEN_FILE, 0o600)
    print(f"Token saved to {TOKEN_FILE} (scope: drive.readonly)")


def _test(creds):
    from googleapiclient.discovery import build
    svc = build("drive", "v3", credentials=creds, cache_discovery=False)
    res = svc.files().list(pageSize=3, fields="files(name)").execute()
    print(f"Success! Drive is readable ({len(res.get('files', []))} sample files listed).")


def main():
    if "--browser" in sys.argv:
        from gmail_auth import browser_flow
        creds = browser_flow(CREDS_FILE, TOKEN_FILE, SCOPES)
        os.chmod(TOKEN_FILE.parent, 0o700)
        _test(creds)
        return
    from google.oauth2.credentials import Credentials
    from requests_oauthlib import OAuth2Session
    import requests
    cfg = json.loads(CREDS_FILE.read_text())["installed"]
    redirect_uri = "http://localhost"
    oauth = OAuth2Session(client_id=cfg["client_id"], redirect_uri=redirect_uri, scope=SCOPES)
    url, _ = oauth.authorization_url("https://accounts.google.com/o/oauth2/auth", access_type="offline", prompt="consent")
    print("Open this URL (phone or any browser), sign in as Rafael, approve READ-ONLY Drive access.")
    print("The last page will fail to load; copy the code= value from its address bar.\n")
    print(url + "\n")
    code = input("Paste the code= value (or the whole http://localhost/?code=... address): ").strip()
    if "code=" in code:
        from urllib.parse import parse_qs, urlparse
        code = parse_qs(urlparse(code).query).get("code", [""])[0]
    if not code:
        sys.exit("No code provided.")
    token_uri = cfg.get("token_uri", "https://oauth2.googleapis.com/token")
    r = requests.post(token_uri, data={"code": code, "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
                                       "redirect_uri": redirect_uri, "grant_type": "authorization_code"}, timeout=30)
    r.raise_for_status()
    tok = r.json()
    creds = Credentials(token=tok.get("access_token"), refresh_token=tok.get("refresh_token"), token_uri=token_uri,
                        client_id=cfg["client_id"], client_secret=cfg["client_secret"], scopes=SCOPES)
    _save(creds)
    _test(creds)


if __name__ == "__main__":
    main()
