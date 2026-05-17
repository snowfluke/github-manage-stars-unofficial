"""Validation for list names and category configs."""
from __future__ import annotations

MAX_LIST_NAME_LENGTH = 32
MAX_LISTS_PER_ACCOUNT = 32


def validate_list_name(name: str, *, existing: set[str] | None = None) -> str | None:
    """Return an error message, or None if the name is valid.

    Rules enforced by GitHub's UI (observed, undocumented):
      - non-empty after stripping whitespace
      - up to 32 characters
      - case-insensitive uniqueness on the account

    `existing` should be the set of already-used names on the account
    (or planned names within the same proposed config).
    """
    s = name.strip()
    if not s:
        return "name is empty"
    if len(s) > MAX_LIST_NAME_LENGTH:
        return f"name is {len(s)} chars; max is {MAX_LIST_NAME_LENGTH}"
    if existing is not None:
        lowered = {e.strip().lower() for e in existing}
        if s.lower() in lowered:
            return f"name {s!r} duplicates an existing list (case-insensitive)"
    return None


def validate_category_set(categories: list[dict]) -> list[str]:
    """Validate a full set of proposed categories.

    Each category should be {"name": str, "description": str, "patterns": [str]}.
    Returns a list of error messages — empty list means OK.
    """
    errors: list[str] = []
    if len(categories) > MAX_LISTS_PER_ACCOUNT:
        errors.append(
            f"{len(categories)} categories > GitHub limit of {MAX_LISTS_PER_ACCOUNT} lists per account"
        )
    seen_names: set[str] = set()
    for i, cat in enumerate(categories):
        name = cat.get("name", "").strip()
        if not name:
            errors.append(f"category #{i + 1}: missing name")
            continue
        err = validate_list_name(name, existing=seen_names)
        if err:
            errors.append(f"category #{i + 1} ({name!r}): {err}")
        seen_names.add(name)
        if not isinstance(cat.get("patterns", []), list):
            errors.append(f"category #{i + 1} ({name!r}): patterns must be a list")
    return errors
