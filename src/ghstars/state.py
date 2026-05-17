"""Per-account resume state — created list IDs and assigned repos."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import config


@dataclass
class State:
    username: str
    created_lists: dict[str, int] = field(default_factory=dict)
    assigned_repos: set[str] = field(default_factory=set)

    @property
    def path(self) -> Path:
        return config.state_file(self.username)

    @classmethod
    def load(cls, username: str) -> "State":
        path = config.state_file(username)
        if not path.exists():
            return cls(username=username)
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return cls(username=username)
        return cls(
            username=username,
            created_lists=dict(data.get("created_lists", {})),
            assigned_repos=set(data.get("assigned_repos", [])),
        )

    def save(self) -> None:
        config.ensure_dirs()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "username": self.username,
            "created_lists": dict(sorted(self.created_lists.items())),
            "assigned_repos": sorted(self.assigned_repos),
        }
        self.path.write_text(json.dumps(payload, indent=2))

    def reset(self) -> None:
        self.created_lists.clear()
        self.assigned_repos.clear()
        self.save()
