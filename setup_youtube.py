#!/usr/bin/env python3
"""
YOUTUBE SETUP  —  run this ONCE on your computer to get your refresh token.
After you have the token, add it to GitHub Secrets and never run this again.

HOW TO USE:
  1. Go to https://console.cloud.google.com
  2. New Project → name it wc2026
  3. APIs & Services → Library → search "YouTube Data API v3" → Enable
  4. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
  5. Application type = Desktop app → Create → Download JSON
  6. Rename the downloaded file to client_secret.json
  7. Put client_secret.json in this folder
  8. Run:  python3 setup_youtube.py
  9. A browser opens → sign in → allow access
  10. Copy the 3 values printed and add them as GitHub Secrets:
       YOUTUBE_CLIENT_ID
       YOUTUBE_CLIENT_SECRET
       YOUTUBE_REFRESH_TOKEN
"""

import json, sys, os

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
except ImportError:
    sys.exit("Run first:  pip install google-auth-oauthlib google-auth")

SECRET_FILE = "client_secret.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

def main():
    if not os.path.exists(SECRET_FILE):
        print(f"ERROR: {SECRET_FILE} not found.")
        print("Download it from Google Cloud Console → Credentials → OAuth 2.0 Client")
        sys.exit(1)

    print("Opening browser for Google sign-in...")
    flow = InstalledAppFlow.from_client_secrets_file(SECRET_FILE, scopes=SCOPES)
    creds = flow.run_local_server(port=0)

    with open(SECRET_FILE) as f:
        secret = json.load(f)
    client = secret.get("installed") or secret.get("web", {})

    print("\n" + "="*60)
    print("SUCCESS! Add these 3 values to GitHub Secrets:")
    print("="*60)
    print(f"\nYOUTUBE_CLIENT_ID:\n  {client.get('client_id','')}")
    print(f"\nYOUTUBE_CLIENT_SECRET:\n  {client.get('client_secret','')}")
    print(f"\nYOUTUBE_REFRESH_TOKEN:\n  {creds.refresh_token}")
    print("\n" + "="*60)
    print("GitHub Secrets path:")
    print("  Your repo → Settings → Secrets and variables → Actions → New repository secret")
    print("="*60)

    # Also save locally for reference
    with open("youtube_tokens.json", "w") as f:
        json.dump({
            "client_id": client.get("client_id",""),
            "client_secret": client.get("client_secret",""),
            "refresh_token": creds.refresh_token
        }, f, indent=2)
    print("\nAlso saved to youtube_tokens.json (keep this private, never commit it)")

if __name__ == "__main__":
    main()
