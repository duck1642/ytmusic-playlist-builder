# Contributing

Thanks for your interest in improving YouTube Music Playlist Builder.

## Before You Start

- Use Python 3.13 or newer.
- Create a virtual environment and install the dependencies from `requirements.txt`.
- Keep OAuth credentials, `config.yaml`, local state, cache files, logs, and generated output local. Do not commit them.

## Development Checks

Run the test suite before opening a pull request:

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=work/pytest-tmp
```

You can also validate artist files without using the network:

```powershell
.\.venv\Scripts\python.exe build_playlists.py --validate-format
```

Changes that use the YouTube Music API should be tested carefully with a personal configuration. Avoid creating or modifying real playlists unless it is necessary for the change.

## Pull Requests

- Keep changes focused and explain the reason for the change.
- Add or update tests when behavior changes.
- Update the README or other documentation when user-facing behavior changes.
- Include the checks you ran in the pull request description.
- Do not include credentials, personal artist lists, OAuth tokens, or generated runtime files.
