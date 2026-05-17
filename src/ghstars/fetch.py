"""Fetch a user's starred repositories via GitHub's public REST API.

We use the documented REST endpoint `/users/{username}/starred` here, not the
unofficial UI endpoints — this gives us a stable shape with numeric repo IDs.

Unauthenticated callers get the standard 60-requests/hour rate limit, which
covers ~6,000 stars per hour. Provide a token via the `GHSTARS_TOKEN` env
variable for the bumped 5,000/hour limit if you have a large library.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable

import requests

from .categorize import Repo

API_BASE = "https://api.github.com"
PER_PAGE = 100


def _headers(token: str | None) -> dict:
    # The REST API doesn't care about UA spoofing, but be a polite client
    # and identify ourselves by name + version + project URL.
    from . import __version__
    h = {
        "accept": "application/vnd.github.star+json",
        "user-agent": (
            f"ghstars/{__version__} "
            "(+https://github.com/snowfluke/github-manage-stars-unofficial)"
        ),
        "x-github-api-version": "2022-11-28",
    }
    if token:
        h["authorization"] = f"Bearer {token}"
    return h


def fetch_starred(
    username: str,
    *,
    token: str | None = None,
    progress: Callable[[int, int | None], None] | None = None,
    sleep_between_pages: float = 0.5,
) -> list[Repo]:
    """Pull every starred repo for `username` and return Repo objects."""
    token = token or os.environ.get("GHSTARS_TOKEN")
    out: list[Repo] = []
    page = 1
    while True:
        url = f"{API_BASE}/users/{username}/starred"
        r = requests.get(
            url,
            headers=_headers(token),
            params={"per_page": PER_PAGE, "page": page},
            timeout=30,
        )
        if r.status_code == 403 and "rate limit" in r.text.lower():
            reset = r.headers.get("X-RateLimit-Reset")
            raise RuntimeError(
                f"GitHub rate limit hit on page {page}. Resets at unix ts {reset}. "
                "Set GHSTARS_TOKEN for the 5,000/hour limit."
            )
        if r.status_code != 200:
            raise RuntimeError(f"fetch_starred page {page}: HTTP {r.status_code} — {r.text[:200]}")

        items = r.json()
        if not items:
            break

        for entry in items:
            # With `application/vnd.github.star+json` the shape is
            #   {"starred_at": "...", "repo": {...}}
            # Without it, items are bare repo objects.
            repo = entry["repo"] if isinstance(entry, dict) and "repo" in entry else entry
            out.append(Repo(
                name=repo.get("full_name", ""),
                id=int(repo.get("id", 0)),
                description=repo.get("description") or "",
                language=repo.get("language"),
                topics=list(repo.get("topics") or []),
                stars=int(repo.get("stargazers_count") or 0),
                archived=bool(repo.get("archived")),
                is_fork=bool(repo.get("fork")),
                updated_at=str(repo.get("updated_at") or ""),
            ))

        if progress:
            progress(len(out), None)

        if len(items) < PER_PAGE:
            break
        page += 1
        time.sleep(sleep_between_pages)
    return out


def dump_jsonl(repos: list[Repo], path: Path) -> None:
    Path(path).write_text(
        "\n".join(
            json.dumps({
                "name": r.name,
                "id": r.id,
                "desc": r.description,
                "lang": r.language,
                "topics": r.topics,
                "stars": r.stars,
                "archived": r.archived,
                "fork": r.is_fork,
                "updated": r.updated_at,
            })
            for r in repos
        ) + "\n"
    )


def dump_json_array(repos: list[Repo], path: Path) -> None:
    """Convenience dump suitable for feeding to an LLM."""
    data = [
        {
            "name": r.name,
            "description": r.description,
            "language": r.language,
            "topics": r.topics,
            "stars": r.stars,
            "archived": r.archived,
            "fork": r.is_fork,
            "updated_at": r.updated_at,
        }
        for r in repos
    ]
    Path(path).write_text(json.dumps(data, indent=2))
