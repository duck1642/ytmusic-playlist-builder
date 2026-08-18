import json
from pathlib import Path

import pytest
import ytmusicapi

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

    def fake_setup_oauth(
        client_id: str,
        client_secret: str,
        *,
        filepath: str,
        session: object,
        open_browser: bool,
    ) -> None:
        calls.append((client_id, client_secret, filepath, session, open_browser))
        Path(filepath).write_text("{}", encoding="utf-8")

    monkeypatch.setattr(ytmusicapi, "setup_oauth", fake_setup_oauth)

    result = setup_oauth(client_file, auth_file, open_browser=False)

    assert result == auth_file
    assert auth_file.is_file()
    assert calls[0][0:3] == ("client-id", "client-secret", str(auth_file))
    assert calls[0][3].get_adapter("https://").ssl_context.maximum_version.name == "TLSv1_2"
    assert calls[0][4] is False


def test_load_oauth_client_rejects_missing_secret(tmp_path: Path) -> None:
    client_file = tmp_path / "client_secret.json"
    client_file.write_text('{"client_id": "client-id"}', encoding="utf-8")

    with pytest.raises(AuthError, match="client_id and client_secret"):
        load_oauth_client(client_file)
