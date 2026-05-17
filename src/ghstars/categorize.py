"""Rules-based repository categorisation.

A Category has a name, a description (used as the list description on GitHub),
and a list of regex patterns matched against a repo's name + description + topics.
Rules are evaluated in order and first match wins, so put narrower rules first.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class Category:
    name: str
    description: str = ""
    patterns: list[str] = field(default_factory=list)
    # Language match (lower-cased). If set and the repo's primary language matches,
    # the repo lands here regardless of patterns.
    language: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Category":
        return cls(
            name=str(d["name"]),
            description=str(d.get("description", "")),
            patterns=[str(p) for p in d.get("patterns") or []],
            language=(d.get("language") or "").lower() or None,
        )

    def matches(self, blob: str, language: str | None) -> bool:
        if self.language and language and language.lower() == self.language:
            return True
        if not self.patterns:
            return False
        for pat in self.patterns:
            if re.search(pat, blob):
                return True
        return False


@dataclass
class Repo:
    name: str               # "owner/repo"
    id: int                 # GitHub numeric database id
    description: str
    language: str | None
    topics: list[str]
    stars: int
    archived: bool
    is_fork: bool
    updated_at: str

    @classmethod
    def from_dict(cls, d: dict) -> "Repo":
        return cls(
            name=str(d.get("name", "")),
            id=int(d.get("id", 0)),
            description=str(d.get("desc") or d.get("description") or ""),
            language=(d.get("lang") or d.get("language") or None),
            topics=list(d.get("topics") or []),
            stars=int(d.get("stars") or 0),
            archived=bool(d.get("archived")),
            is_fork=bool(d.get("fork") or d.get("is_fork")),
            updated_at=str(d.get("updated") or d.get("updated_at") or ""),
        )

    @property
    def search_blob(self) -> str:
        return " ".join([
            self.name,
            self.description,
            " ".join(self.topics),
        ]).lower()


ARCHIVED_BUCKET = "Archived"
FALLBACK_BUCKET = "Other"


def categorize(
    repos: Iterable[Repo],
    categories: list[Category],
    *,
    archived_bucket: str = ARCHIVED_BUCKET,
    fallback_bucket: str = FALLBACK_BUCKET,
) -> dict[str, list[Repo]]:
    """Place each repo into one bucket. Archived repos short-circuit to their own bucket
    if a category by that name exists."""
    has_archived_bucket = any(c.name == archived_bucket for c in categories)
    has_fallback_bucket = any(c.name == fallback_bucket for c in categories)
    buckets: dict[str, list[Repo]] = {c.name: [] for c in categories}
    if not has_fallback_bucket:
        buckets[fallback_bucket] = []

    for repo in repos:
        if repo.archived and has_archived_bucket:
            buckets[archived_bucket].append(repo)
            continue
        blob = repo.search_blob
        placed = False
        for cat in categories:
            if cat.name == archived_bucket:
                continue
            if cat.matches(blob, repo.language):
                buckets[cat.name].append(repo)
                placed = True
                break
        if not placed:
            buckets[fallback_bucket].append(repo)
    return buckets


# ---- JSON load/save -----------------------------------------------------

def load_categories_json(path: Path) -> list[Category]:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array of category objects")
    return [Category.from_dict(d) for d in data]


def dump_categories_json(categories: list[Category], path: Path) -> None:
    out = [
        {
            "name": c.name,
            "description": c.description,
            "patterns": c.patterns,
            **({"language": c.language} if c.language else {}),
        }
        for c in categories
    ]
    Path(path).write_text(json.dumps(out, indent=2))


def load_stars_jsonl(path: Path) -> list[Repo]:
    out: list[Repo] = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(Repo.from_dict(json.loads(line)))
    return out
