"""Automatic local and Google Drive export service.

Handles copying exported video clips to a local folder and uploading
to Google Drive when configured.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_LOCAL_DIR = Path("/app/exports")
FALLBACK_LOCAL_DIR = Path("/exports")


def get_local_export_dir() -> Path:
    configured = os.getenv("LOCAL_EXPORT_DIR")
    if configured:
        directory = Path(configured)
    elif DEFAULT_LOCAL_DIR.exists() or DEFAULT_LOCAL_DIR.parent.exists():
        directory = DEFAULT_LOCAL_DIR
    elif FALLBACK_LOCAL_DIR.exists():
        directory = FALLBACK_LOCAL_DIR
    else:
        directory = Path("./exports")
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Could not create local export dir %s: %s", directory, exc)
    return directory


def sanitize_filename(filename: str) -> str:
    cleaned = filename.strip()
    for character in ('"', "'", "\r", "\n", "/", "\\", ":", "*", "?", "<", ">", "|"):
        cleaned = cleaned.replace(character, "_")
    if not cleaned.lower().endswith(".mp4"):
        cleaned = f"{cleaned}.mp4"
    return cleaned


def save_to_local_exports(source_path: Path, filename: str) -> Optional[Path]:
    """Copy an exported file to the local exports folder."""
    if not source_path or not source_path.exists():
        logger.warning("Cannot copy missing export file: %s", source_path)
        return None

    target_dir = get_local_export_dir()
    clean_name = sanitize_filename(filename)
    target_path = target_dir / clean_name

    if target_path.exists():
        stem = target_path.stem
        timestamp = int(time.time())
        target_path = target_dir / f"{stem}_{timestamp}.mp4"

    try:
        shutil.copy2(source_path, target_path)
        logger.info("Successfully copied export to local folder: %s", target_path)
        return target_path
    except Exception as exc:
        logger.error("Failed to copy export to %s: %s", target_path, exc)
        return None


def _get_service_account_token(service_account_info: Dict[str, Any]) -> Optional[str]:
    """Sign a JWT and obtain an OAuth2 access token for Google Drive."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError:
        logger.warning("cryptography package not available for Google Service Account auth")
        return None

    client_email = service_account_info.get("client_email")
    private_key_pem = service_account_info.get("private_key")
    token_uri = service_account_info.get("token_uri", "https://oauth2.googleapis.com/token")

    if not client_email or not private_key_pem:
        logger.warning("Invalid service account info: missing client_email or private_key")
        return None

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iss": client_email,
        "scope": "https://www.googleapis.com/auth/drive.file",
        "aud": token_uri,
        "exp": now + 3600,
        "iat": now,
    }

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    header_bytes = b64url(json.dumps(header).encode("utf-8"))
    payload_bytes = b64url(json.dumps(payload).encode("utf-8"))
    signing_input = f"{header_bytes}.{payload_bytes}".encode("utf-8")

    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None,
        )
        signature = private_key.sign(
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        jwt = f"{header_bytes}.{payload_bytes}.{b64url(signature)}"

        response = requests.post(
            token_uri,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": jwt,
            },
            timeout=15,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        logger.error(
            "Google OAuth token request failed with %d: %s",
            response.status_code,
            response.text[:500],
        )
    except Exception as exc:
        logger.error("Failed to generate Google Drive access token: %s", exc)

    return None


def _get_oauth_refresh_token() -> Optional[str]:
    """Exchange an OAuth2 refresh token for an access token."""
    client_id = os.getenv("GDRIVE_CLIENT_ID")
    client_secret = os.getenv("GDRIVE_CLIENT_SECRET")
    refresh_token = os.getenv("GDRIVE_REFRESH_TOKEN")

    if not (client_id and client_secret and refresh_token):
        return None

    token_uri = os.getenv("GDRIVE_TOKEN_URI", "https://oauth2.googleapis.com/token")
    try:
        response = requests.post(
            token_uri,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        logger.error(
            "Google Drive refresh token exchange failed with %d: %s",
            response.status_code,
            response.text[:500],
        )
    except Exception as exc:
        logger.error("Failed to exchange Google Drive refresh token: %s", exc)

    return None


def get_gdrive_access_token() -> Optional[str]:
    """Retrieve an active Google Drive API access token."""
    direct_token = os.getenv("GDRIVE_ACCESS_TOKEN")
    if direct_token:
        return direct_token.strip()

    # Check for Service Account JSON in env or file path
    service_account_path = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON")
    service_account_raw = os.getenv("GDRIVE_SERVICE_ACCOUNT_KEY")

    if service_account_raw:
        try:
            info = json.loads(service_account_raw)
            token = _get_service_account_token(info)
            if token:
                return token
        except Exception as exc:
            logger.warning("Could not parse GDRIVE_SERVICE_ACCOUNT_KEY: %s", exc)

    if service_account_path and Path(service_account_path).is_file():
        try:
            info = json.loads(Path(service_account_path).read_text(encoding="utf-8"))
            token = _get_service_account_token(info)
            if token:
                return token
        except Exception as exc:
            logger.warning("Could not read GDRIVE_SERVICE_ACCOUNT_JSON: %s", exc)

    # Check OAuth2 refresh token
    return _get_oauth_refresh_token()


def upload_to_google_drive(file_path: Path, filename: str) -> Optional[Dict[str, Any]]:
    """Upload a file to Google Drive using the Drive v3 API."""
    enabled = os.getenv("GDRIVE_ENABLED", "true").lower() not in ("false", "0", "no")
    if not enabled:
        return None

    folder_id = os.getenv("GDRIVE_FOLDER_ID", "").strip()
    token = get_gdrive_access_token()

    if not token or not folder_id:
        logger.info(
            "Google Drive upload not configured. Set GDRIVE_FOLDER_ID and "
            "GDRIVE_SERVICE_ACCOUNT_JSON in .env to enable auto-upload."
        )
        return None

    if not file_path.is_file():
        logger.warning("File to upload does not exist: %s", file_path)
        return None

    file_size = file_path.stat().st_size
    clean_name = sanitize_filename(filename)

    metadata: Dict[str, Any] = {
        "name": clean_name,
        "parents": [folder_id],
        "mimeType": "video/mp4",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(file_size),
    }

    try:
        # Initiate resumable upload session
        init_response = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
            headers=headers,
            json=metadata,
            timeout=30,
        )
        if init_response.status_code != 200:
            logger.error(
                "Google Drive resumable upload init failed with %d: %s",
                init_response.status_code,
                init_response.text[:500],
            )
            return None

        upload_url = init_response.headers.get("Location")
        if not upload_url:
            logger.error("Google Drive did not return an upload Location header")
            return None

        # Upload file content
        with file_path.open("rb") as stream:
            upload_headers = {
                "Content-Length": str(file_size),
                "Content-Type": "video/mp4",
            }
            put_response = requests.put(
                upload_url,
                headers=upload_headers,
                data=stream,
                timeout=180,
            )

        if put_response.status_code in (200, 201):
            data = put_response.json()
            file_id = data.get("id")
            web_link = f"https://drive.google.com/file/d/{file_id}/view"
            logger.info("Successfully uploaded %s to Google Drive: %s", clean_name, web_link)
            return {
                "file_id": file_id,
                "name": clean_name,
                "web_view_link": web_link,
            }

        logger.error(
            "Google Drive upload PUT failed with %d: %s",
            put_response.status_code,
            put_response.text[:500],
        )
    except Exception as exc:
        logger.error("Error during Google Drive upload for %s: %s", clean_name, exc)

    return None


def process_post_export(file_path: Path, filename: str) -> Dict[str, Any]:
    """Execute both local copy and Google Drive auto-upload for an exported clip."""
    results: Dict[str, Any] = {
        "local_path": None,
        "gdrive": None,
    }

    local_path = save_to_local_exports(file_path, filename)
    if local_path:
        results["local_path"] = str(local_path)

    gdrive_result = upload_to_google_drive(file_path, filename)
    if gdrive_result:
        results["gdrive"] = gdrive_result

    return results

