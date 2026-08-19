from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .network import create_requests_session


_GOOGLE_DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
_GOOGLE_DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


class AuthError(RuntimeError):
    """Raised when local YouTube Music authentication cannot be prepared."""


@dataclass(frozen=True, slots=True)
class OAuthClient:
    client_id: str
    client_secret: str


def load_oauth_client(path: Path) -> OAuthClient:
    """Read Google OAuth client credentials from a downloaded JSON file."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AuthError(f"OAuth client file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise AuthError(f"Invalid JSON in OAuth client file: {path}") from error
    except OSError as error:
        raise AuthError(f"Could not read OAuth client file: {error}") from error

    if not isinstance(raw, dict):
        raise AuthError("OAuth client file must contain a JSON object")

    candidates: list[dict[str, Any]] = [raw]
    for key in ("installed", "web"):
        nested = raw.get(key)
        if isinstance(nested, dict):
            candidates.insert(0, nested)

    for candidate in candidates:
        client_id = candidate.get("client_id")
        client_secret = candidate.get("client_secret")
        if (
            isinstance(client_id, str)
            and client_id.strip()
            and isinstance(client_secret, str)
            and client_secret.strip()
        ):
            return OAuthClient(client_id.strip(), client_secret.strip())

    raise AuthError("OAuth client file must contain client_id and client_secret")


def setup_oauth(client_file: Path, auth_file: Path, *, open_browser: bool = True) -> Path:
    """Run ytmusicapi's OAuth device flow and save its token locally."""
    client = load_oauth_client(client_file)
    try:
        from ytmusicapi.auth.oauth import OAuthCredentials
        from ytmusicapi.auth.oauth.token import RefreshingToken
        from ytmusicapi.constants import OAUTH_SCOPE, OAUTH_TOKEN_URL
    except ImportError as error:
        raise AuthError(
            "ytmusicapi is required for OAuth setup; install requirements.txt"
        ) from error

    class GoogleDeviceOAuthCredentials(OAuthCredentials):
        """Use Google's current device authorization endpoints."""

        def get_code(self) -> Any:
            response = self._send_request(
                _GOOGLE_DEVICE_CODE_URL,
                data={"scope": OAUTH_SCOPE},
            )
            return response.json()

        def token_from_code(self, device_code: str) -> Any:
            response = self._send_request(
                OAUTH_TOKEN_URL,
                data={
                    "client_secret": self.client_secret,
                    "device_code": device_code,
                    "grant_type": _GOOGLE_DEVICE_GRANT_TYPE,
                },
            )
            return response.json()

    auth_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        session = create_requests_session()
        credentials = GoogleDeviceOAuthCredentials(
            client.client_id,
            client.client_secret,
            session=session,
        )
        RefreshingToken.prompt_for_token(
            credentials,
            open_browser=open_browser,
            to_file=str(auth_file),
        )
    except Exception as error:
        raise AuthError(f"OAuth setup failed: {error}") from error

    if not auth_file.is_file():
        raise AuthError(f"OAuth setup did not create token file: {auth_file}")
    return auth_file
