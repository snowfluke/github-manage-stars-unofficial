"""HTML parsing helpers for GitHub UI fragments."""
from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag


@dataclass
class ListInfo:
    slug: str
    name: str
    list_id: int = 0


def _has_input(form: Tag, name: str, value: str | None = None) -> bool:
    inp = form.find("input", {"name": name})
    if not inp:
        return False
    if value is None:
        return True
    return inp.get("value") == value


def is_delete_form(form: Tag) -> bool:
    return _has_input(form, "_method", "delete")


def is_new_list_form(form: Tag) -> bool:
    return form.find("input", {"name": "user_list[name]"}) is not None


def is_repo_lists_form(form: Tag) -> bool:
    if not _has_input(form, "_method", "put"):
        return False
    return form.find("input", attrs={"name": re.compile(r"^list_ids")}) is not None


def extract_csrf_from_form(form: Tag) -> str | None:
    inp = form.find("input", {"name": "authenticity_token"})
    if inp and inp.get("value"):
        return inp["value"]
    return None


def find_form(html: str, predicate) -> Tag | None:
    soup = BeautifulSoup(html, "html.parser")
    for form in soup.find_all("form"):
        if predicate(form):
            return form
    return None


def parse_user_lists(html: str, username: str) -> list[ListInfo]:
    """Extract (slug, name) for every star list visible on a user's stars tab."""
    soup = BeautifulSoup(html, "html.parser")
    pat = re.compile(rf"^/stars/{re.escape(username)}/lists/([^/?#]+)$")
    found: dict[str, ListInfo] = {}
    for a in soup.find_all("a", href=True):
        m = pat.match(a["href"])
        if not m:
            continue
        slug = m.group(1)
        if slug in {"new", "edit"}:
            continue
        name = a.get_text(strip=True) or slug
        # Strip suffixes like "X repository/repositories" the user-card UI appends.
        name = re.sub(r"\s*\d+\s*repositor(?:y|ies)\s*$", "", name).strip()
        if slug not in found:
            found[slug] = ListInfo(slug=slug, name=name)
    return sorted(found.values(), key=lambda x: x.slug)


@dataclass
class RepoListContext:
    csrf: str | None
    lists: list[dict]  # [{"id": int, "name": str, "checked": bool}]


def parse_repo_list_fragment(html: str) -> RepoListContext:
    soup = BeautifulSoup(html, "html.parser")
    form = next(
        (f for f in soup.find_all("form") if is_repo_lists_form(f)),
        None,
    )
    csrf = extract_csrf_from_form(form) if form else None

    lists: list[dict] = []
    # Modern GitHub renders the menu as <button data-input-name="list_ids[]" data-value="<id>">
    for btn in soup.find_all("button", attrs={"data-input-name": "list_ids[]"}):
        val = btn.get("data-value", "")
        if not val.isdigit():
            continue
        label = btn.find("span", class_="ActionListItem-label")
        name_text = label.get_text(" ", strip=True) if label else btn.get_text(" ", strip=True)
        lists.append({
            "id": int(val),
            "name": name_text.strip(),
            "checked": btn.get("aria-selected") == "true",
        })
    return RepoListContext(csrf=csrf, lists=lists)


def extract_first_flash_error(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    el = soup.find(class_=re.compile(r"flash-error|\berror\b"))
    if not el:
        return None
    text = el.get_text(" ", strip=True)
    return text[:200] if text else None
