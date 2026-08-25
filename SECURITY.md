# Security Policy

## Scope

YouTube Music Playlist Builder is a local Windows/Python utility. It does not provide a hosted service.

## Keep Credentials Private

Never commit or share:

- `auth/client_secret.json`
- `auth/oauth.json`
- `config.yaml`
- Personal artist lists or generated runtime data

If credentials are exposed, revoke or rotate them before reporting the issue.

## Reporting a Vulnerability

Please do not disclose unreported vulnerabilities in a public issue.

Use GitHub's private vulnerability reporting for this repository if it is available. Otherwise, contact the repository owner privately through GitHub.

Include the affected version or commit, reproduction steps, expected and actual behavior, and the potential impact. Avoid including credentials or other private data.
