"""First-time Gmail OAuth2 authorization. Run once to generate token.json."""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDS_FILE = os.path.expanduser('~/empire-repo/backend/credentials.json')
TOKEN_FILE = os.path.expanduser('~/empire-repo/backend/token.json')

def main():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        print(f"Token saved to {TOKEN_FILE}")

    # Test it works
    from googleapiclient.discovery import build
    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = results.get('messages', [])
    print(f"Success! Found {len(messages)} recent messages.")

if __name__ == '__main__':
    main()
