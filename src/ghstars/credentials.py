"""Secure local storage for GitHub session cookies."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import config

# Cookies we actually need from a GitHub session, in priority order.
# user_session (and the same_site mirror) and _gh_sess are what GitHub
# authenticates against; the rest are nice-to-have but not strictly required.
REQUIRED_COOKIES = ("user_session", "_gh_sess")
OPTIONAL_COOKIES = (
    "__Host-user_session_same_site",
    "dotcom_user",
    "logged_in",
    "_device_id",
    "_octo",
)


@dataclass(frozen=True)
class Credentials:
    cookies: dict[str, str]

    @property
    def username(self) -> str | None:
        return self.cookies.get("dotcom_user")


def parse_curl_cookie_header(text: str) -> dict[str, str]:
    """Pull cookies from either a `-b 'k=v; ...'` curl arg or a raw cookie header."""
    s = text.strip()
    for prefix in ("-b ", "--cookie "):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
    if s.startswith("'") and s.endswith("'"):
        s = s[1:-1]
    elif s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    if s.lower().startswith("cookie:"):
        s = s.split(":", 1)[1].strip()

    out: dict[str, str] = {}
    for part in s.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def save(creds: Credentials) -> Path:
    config.ensure_dirs()
    path = config.CREDENTIALS_FILE
    path.write_text(json.dumps(creds.cookies, indent=2))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def load() -> Credentials | None:
    path = config.CREDENTIALS_FILE
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return Credentials(cookies={str(k): str(v) for k, v in data.items()})


def clear() -> bool:
    path = config.CREDENTIALS_FILE
    if not path.exists():
        return False
    path.unlink()
    return True


def missing_required(cookies: dict[str, str]) -> list[str]:
    return [c for c in REQUIRED_COOKIES if not cookies.get(c)]
