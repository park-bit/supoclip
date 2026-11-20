"""Interactive script to connect personal Google Drive via OAuth 2.0.

Usage:
    python scripts/connect_gdrive.py [CLIENT_SECRET_JSON_PATH or CLIENT_ID] [CLIENT_SECRET]
"""

import http.server
import json
import os
import re
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

PORT = 8085
REDIRECT_URI = f"http://localhost:{PORT}"
SCOPE = "https://www.googleapis.com/auth/drive.file"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


def update_env_file(file_path: Path, updates: dict[str, str]) -> None:
    if not file_path.exists():
        return
    content = file_path.read_text(encoding="utf-8")
    for key, value in updates.items():
        pattern = rf"^{key}=.*$"
        new_line = f"{key}={value}"
        if re.search(pattern, content, flags=re.MULTILINE):
            content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
        else:
            content += f"\n{new_line}"
    file_path.write_text(content, encoding="utf-8")
    print(f"Updated {file_path}")


def get_or_create_folder(access_token: str, folder_name: str = "SupoClip Exports") -> str:
    """Find or create the SupoClip Exports folder in user's Google Drive."""
    query = urllib.parse.quote(f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false")
    req = urllib.request.Request(
        f"{DRIVE_FILES_URL}?q={query}&fields=files(id,name)",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        files = data.get("files", [])
        if files:
            folder_id = files[0]["id"]
            print(f"Found existing Google Drive folder '{folder_name}': {folder_id}")
            return folder_id

    create_body = json.dumps({
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }).encode("utf-8")

    create_req = urllib.request.Request(
        DRIVE_FILES_URL,
        data=create_body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(create_req) as resp:
        created = json.loads(resp.read().decode())
        folder_id = created["id"]
        print(f"Created new Google Drive folder '{folder_name}': {folder_id}")
        return folder_id


def exchange_code_for_tokens(client_id: str, client_secret: str, auth_code: str) -> dict:
    payload = urllib.parse.urlencode({
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    req = urllib.request.Request(TOKEN_URL, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode()
        print(f"Error exchanging authorization code: {exc.code} {error_body}")
        raise


def run_oauth_flow(client_id: str, client_secret: str) -> None:
    auth_code_holder = {"code": None}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            if "code" in query:
                auth_code_holder["code"] = query["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"""
                <html>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: #16a34a;">Google Drive Connected Successfully!</h2>
                    <p>You can close this tab and return to your terminal.</p>
                </body>
                </html>
                """)
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Failed: No authorization code received.")

        def log_message(self, format, *args):
            return

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        })
    )

    print("=" * 60, flush=True)
    print("STEP 1: Open the link below in your browser to sign in:", flush=True)
    print("=" * 60, flush=True)
    print(auth_url, flush=True)
    print("=" * 60, flush=True)

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    try:
        server = http.server.HTTPServer(("127.0.0.1", PORT), CallbackHandler)
        server.timeout = 180
        print(f"\nWaiting for authorization redirect on {REDIRECT_URI}...", flush=True)
        while not auth_code_holder["code"]:
            server.handle_request()
    except Exception as exc:
        print(f"Note: Local server listener stopped: {exc}")

    code = auth_code_holder["code"]
    if not code:
        print("\nIf redirect did not reach the local server automatically,")
        code_input = input("Paste the 'code' or full redirect URL from your browser address bar: ").strip()
        if "code=" in code_input:
            match = re.search(r"code=([^&]+)", code_input)
            code = urllib.parse.unquote(match.group(1)) if match else code_input
        else:
            code = code_input

    if not code:
        print("No authorization code provided.")
        sys.exit(1)

    print("\nExchanging authorization code for tokens...")
    tokens = exchange_code_for_tokens(client_id, client_secret, code)

    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")

    if not refresh_token:
        print("Warning: Google did not return a refresh_token (account already authorized).")
    else:
        print("Obtained refresh token successfully.")

    folder_id = get_or_create_folder(access_token)

    root_dir = Path(__file__).resolve().parent.parent
    env_updates = {
        "GDRIVE_ENABLED": "true",
        "GDRIVE_CLIENT_ID": client_id,
        "GDRIVE_CLIENT_SECRET": client_secret,
        "GDRIVE_REFRESH_TOKEN": refresh_token or "",
        "GDRIVE_FOLDER_ID": folder_id,
    }

    update_env_file(root_dir / ".env", env_updates)
    update_env_file(root_dir / "backend" / ".env", env_updates)

    print("\n" + "=" * 60)
    print("SUCCESS! Google Drive connected successfully.")
    print(f"Folder: 'SupoClip Exports' (ID: {folder_id})")
    print("=" * 60)


def load_credentials_from_json(json_path: Path) -> tuple[str, str]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    installed = data.get("installed") or data.get("web") or data
    client_id = installed.get("client_id", "")
    client_secret = installed.get("client_secret", "")
    return client_id, client_secret


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    client_id = ""
    client_secret = ""

    if arg and Path(arg).is_file():
        client_id, client_secret = load_credentials_from_json(Path(arg))
    elif arg:
        client_id = arg
        client_secret = sys.argv[2] if len(sys.argv) > 2 else ""

    if not client_id or not client_secret:
        client_id = os.getenv("GDRIVE_CLIENT_ID", "").strip() or input("Enter your OAuth Client ID: ").strip()
        client_secret = os.getenv("GDRIVE_CLIENT_SECRET", "").strip() or input("Enter your OAuth Client Secret: ").strip()

    run_oauth_flow(client_id, client_secret)


if __name__ == "__main__":
    main()
