import json
from pathlib import Path

import pytest

from playlist_builder.auth import AuthError, load_oauth_client, setup_oauth


def test_load_oauth_client_supports_google_installed_file(tmp_path: Path) -> None:
    client_file = tmp_path / "client_secret.json"
    client_file.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "client-id",
                    "client_secret": "client-secret",
                }
            }
        ),
        encoding="utf-8",
    )

    client = load_oauth_client(client_file)

    assert client.client_id == "client-id"
    assert client.client_secret == "client-secret"


def test_setup_oauth_saves_token_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client_file = tmp_path / "client_secret.json"
    auth_file = tmp_path / "auth" / "oauth.json"
    client_file.write_text(
        '{"client_id": "client-id", "client_secret": "client-secret"}',
        encoding="utf-8",
    )
    calls: list[tuple[object, ...]] = []

    def fake_prompt_for_token(
        credentials: object,
        *,
        open_browser: bool,
        to_file: str,
    ) -> None:
        calls.append((credentials, open_browser, to_file))
        Path(to_file).write_text("{}", encoding="utf-8")

    from ytmusicapi.auth.oauth.token import RefreshingToken

    monkeypatch.setattr(RefreshingToken, "prompt_for_token", fake_prompt_for_token)

    result = setup_oauth(client_file, auth_file, open_browser=False)

    assert result == auth_file
    assert auth_file.is_file()
    credentials = calls[0][0]
    assert credentials.client_id == "client-id"
    assert credentials.client_secret == "client-secret"
    assert credentials._session.get_adapter("https://").ssl_context.maximum_version.name == "TLSv1_2"
    assert calls[0][1] is False
    assert calls[0][2] == str(auth_file)


def test_setup_oauth_uses_current_google_device_endpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client_file = tmp_path / "client_secret.json"
    auth_file = tmp_path / "oauth.json"
    client_file.write_text(
        '{"client_id": "client-id", "client_secret": "client-secret"}',
        encoding="utf-8",
    )
    captured: list[object] = []

    def fake_prompt_for_token(credentials: object, **_: object) -> None:
        captured.append(credentials)
        auth_file.write_text("{}", encoding="utf-8")

    from ytmusicapi.auth.oauth.token import RefreshingToken

    monkeypatch.setattr(RefreshingToken, "prompt_for_token", fake_prompt_for_token)
    setup_oauth(client_file, auth_file, open_browser=False)
    credentials = captured[0]

    requests: list[tuple[str, dict[str, str]]] = []

    class FakeResponse:
        def __init__(self, payload: dict[str, str]) -> None:
            self.payload = payload

        def json(self) -> dict[str, str]:
            return self.payload

    def fake_send_request(url: str, data: dict[str, str]) -> FakeResponse:
        requests.append((url, dict(data)))
        return FakeResponse({"ok": "true"})

    credentials._send_request = fake_send_request

    credentials.get_code()
    credentials.token_from_code("device-code")

    assert requests[0] == (
        "https://oauth2.googleapis.com/device/code",
        {"scope": "https://www.googleapis.com/auth/youtube"},
    )
    assert requests[1] == (
        "https://oauth2.googleapis.com/token",
        {
            "client_secret": "client-secret",
            "device_code": "device-code",
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        },
    )


def test_load_oauth_client_rejects_missing_secret(tmp_path: Path) -> None:
    client_file = tmp_path / "client_secret.json"
    client_file.write_text('{"client_id": "client-id"}', encoding="utf-8")

    with pytest.raises(AuthError, match="client_id and client_secret"):
        load_oauth_client(client_file)
