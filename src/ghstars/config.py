"""Paths and persisted settings."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _config_dir() -> Path:
    """Resolve XDG-style config directory cross-platform."""
    if env := os.environ.get("GHSTARS_CONFIG_HOME"):
        return Path(env)
    if env := os.environ.get("XDG_CONFIG_HOME"):
        return Path(env) / "ghstars"
    return Path.home() / ".config" / "ghstars"


CONFIG_DIR: Path = _config_dir()
SETTINGS_FILE: Path = CONFIG_DIR / "settings.json"
CREDENTIALS_FILE: Path = CONFIG_DIR / "credentials.json"


def account_dir(username: str) -> Path:
    return CONFIG_DIR / "accounts" / username


def state_file(username: str) -> Path:
    return account_dir(username) / "state.json"


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, 0o700)
    except OSError:
        # filesystem may not support chmod (e.g. Windows) — best effort only
        pass


# ---- settings -----------------------------------------------------------

MIN_ALLOWED_JITTER = 0.3
MAX_REASONABLE_JITTER = 30.0


@dataclass
class Settings:
    jitter_min: float = 1.5
    jitter_max: float = 3.0
    phase_pause_min: float = 4.0
    phase_pause_max: float = 8.0
    retry_attempts: int = 4
    retry_base_seconds: float = 2.0

    def validate(self) -> list[str]:
        """Return a list of human-readable issues. Empty list means OK."""
        issues: list[str] = []
        if self.jitter_min < MIN_ALLOWED_JITTER:
            issues.append(
                f"jitter_min ({self.jitter_min}s) is below the floor of "
                f"{MIN_ALLOWED_JITTER}s — high risk of rate-limiting or account flagging."
            )
        if self.jitter_max < self.jitter_min:
            issues.append("jitter_max must be >= jitter_min")
        if self.jitter_max > MAX_REASONABLE_JITTER:
            issues.append(
                f"jitter_max ({self.jitter_max}s) is huge — your job will take ages. "
                "Consider <= 10s."
            )
        if self.retry_attempts < 0 or self.retry_attempts > 10:
            issues.append("retry_attempts should be between 0 and 10")
        return issues


def load_settings() -> Settings:
    if not SETTINGS_FILE.exists():
        return Settings()
    try:
        data = json.loads(SETTINGS_FILE.read_text())
    except json.JSONDecodeError:
        return Settings()
    defaults = asdict(Settings())
    for k in list(data):
        if k not in defaults:
            data.pop(k)
    return Settings(**{**defaults, **data})


def save_settings(settings: Settings) -> None:
    ensure_dirs()
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2))
    try:
        os.chmod(SETTINGS_FILE, 0o600)
    except OSError:
        pass
