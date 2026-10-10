"""One-time Outlook sign-in for Max (READ-ONLY, Microsoft Graph device code).

Run on the Dell:
    cd ~/empire-repo-main/backend && venv/bin/python outlook_auth.py

It prints a Microsoft link and a short code. Open the link (any device),
enter the code and sign in with the Outlook account Max should read. Access
requested: Mail.Read + offline_access only (read mail; no send, no delete).
The token is saved to ~/.config/empirebox/outlook/token.json (600 perms).

Other options:
    --status    show whether Outlook is signed in (no secrets printed)
    --signout   delete the local token file (Max loses Outlook access)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.max import outlook_reader as orx  # noqa: E402


def main(argv):
    if "--status" in argv:
        s = orx.status()
        print(f"Outlook signed in: {'yes' if s['signed_in'] else 'no'}")
        print(f"Token file: {s['token_path']}")
        if s["signed_in"]:
            print(f"Scopes: {s['scope']}")
            print(f"Saved: {s['saved_at']}")
        return 0
    if "--signout" in argv:
        p = orx.token_path()
        if p.exists():
            p.unlink()
            print(f"Removed {p}. Max no longer has Outlook access.")
        else:
            print("Not signed in; nothing to remove.")
        return 0
    flow = orx.start_device_code()
    print()
    print("=" * 64)
    print("  Outlook sign-in for Max (read-only)")
    print(f"  1. Open:  {flow.get('verification_uri')}")
    print(f"  2. Enter: {flow.get('user_code')}")
    print("  3. Sign in with the Outlook account Max should read and accept.")
    print("     Access asked: read mail only (no send, no delete).")
    print("=" * 64)
    print("Waiting for you to finish (up to 15 minutes)...", flush=True)
    try:
        data = orx.poll_device_code(flow)
    except RuntimeError as e:
        print(f"Not signed in: {e}")
        return 1
    print(f"Done. Outlook connected for Max. Token saved to {orx.token_path()} (600).")
    print(f"Scopes granted: {data.get('scope')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
