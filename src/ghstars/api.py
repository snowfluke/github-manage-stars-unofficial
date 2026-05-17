"""Thin wrapper around GitHub's unofficial UI endpoints for star lists.

THIS USES UNDOCUMENTED ENDPOINTS. They can change at any time. See README
for the full disclaimer.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, Iterable

import requests

from . import parser
from .config import Settings
from .parser import ListInfo, RepoListContext

BASE = "https://github.com"

# Generic fallback used if fake-useragent can't load (e.g. offline). Picked
# to be a plausible, recent Chrome on Windows — not tied to any one user.
FALLBACK_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _pick_user_agent() -> str:
    """Pick a realistic, third-party-supplied Chrome desktop UA per process."""
    try:
        from fake_useragent import UserAgent
        ua = UserAgent(browsers=["Chrome"], os=["Windows", "Mac OS X"], min_version=120.0)
        return ua.random
    except Exception:
        return FALLBACK_USER_AGENT


class APIError(RuntimeError):
    """Raised when the GitHub UI returns an unexpected response."""


class StarsAPI:
    def __init__(
        self,
        username: str,
        cookies: dict[str, str],
        settings: Settings,
        *,
        user_agent: str | None = None,
    ) -> None:
        if not username:
            raise ValueError("username is required")
        self.username = username
        self.settings = settings
        self.session = requests.Session()
        self.session.cookies.update(cookies)
        self.user_agent = user_agent or _pick_user_agent()
        # Sec-CH-UA hints are deliberately omitted: getting them slightly wrong
        # vs. the user-agent string is a stronger fingerprint than not sending
        # them at all. GitHub accepts requests without these hints.
        self.session.headers.update({
            "user-agent": self.user_agent,
            "accept-language": "en-US,en;q=0.9",
            "sec-gpc": "1",
            "dnt": "1",
        })

    # ---------- timing & retries -------------------------------------

    def jitter(self) -> None:
        time.sleep(random.uniform(self.settings.jitter_min, self.settings.jitter_max))

    def long_pause(self) -> None:
        time.sleep(random.uniform(self.settings.phase_pause_min, self.settings.phase_pause_max))

    def _retry(self, fn: Callable[[], requests.Response], label: str) -> requests.Response:
        last_exc: Exception | None = None
        for attempt in range(self.settings.retry_attempts + 1):
            try:
                return fn()
            except requests.exceptions.RequestException as e:
                last_exc = e
                if attempt >= self.settings.retry_attempts:
                    break
                wait = (self.settings.retry_base_seconds ** attempt) + random.uniform(0, 1.5)
                time.sleep(wait)
        raise APIError(f"{label}: exhausted retries ({last_exc!r})") from last_exc

    # ---------- low-level fetch --------------------------------------

    def _get(self, url: str, *, headers: dict | None = None, label: str = "GET") -> requests.Response:
        return self._retry(lambda: self.session.get(url, headers=headers or {}), label)

    def _post(
        self,
        url: str,
        *,
        files: dict | None = None,
        data: dict | None = None,
        headers: dict | None = None,
        allow_redirects: bool = False,
        label: str = "POST",
    ) -> requests.Response:
        return self._retry(
            lambda: self.session.post(
                url,
                files=files,
                data=data,
                headers=headers or {},
                allow_redirects=allow_redirects,
            ),
            label,
        )

    # ---------- public surface ---------------------------------------

    def whoami(self) -> str:
        """Return the displayed account name on the profile page, raising on auth failure."""
        r = self._get(
            f"{BASE}/{self.username}",
            headers={"accept": "text/html"},
            label="whoami",
        )
        if r.status_code != 200:
            raise APIError(f"whoami: HTTP {r.status_code}")
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        return title.text.strip() if title else self.username

    def list_lists(self) -> list[ListInfo]:
        url = (
            f"{BASE}/{self.username}?tab=stars"
            "&user_lists_direction=desc&user_lists_sort=created_at"
        )
        r = self._get(
            url,
            headers={
                "accept": "text/html, application/xhtml+xml",
                "turbo-frame": "user-profile-frame",
            },
            label="list_lists",
        )
        if r.status_code != 200:
            raise APIError(f"list_lists: HTTP {r.status_code}")
        return parser.parse_user_lists(r.text, self.username)

    def fetch_repo_context(self, owner: str, repo: str) -> RepoListContext:
        url = f"{BASE}/{owner}/{repo}/lists?experimental=1"
        r = self._get(
            url,
            headers={
                "accept": "text/fragment+html",
                "x-requested-with": "XMLHttpRequest",
            },
            label=f"fetch_repo_context {owner}/{repo}",
        )
        if r.status_code != 200:
            return RepoListContext(csrf=None, lists=[])
        return parser.parse_repo_list_fragment(r.text)

    def _csrf_from_page(self, page_url: str, form_predicate) -> str:
        r = self._get(page_url, headers={"accept": "text/html"}, label=f"csrf {page_url}")
        if r.status_code != 200:
            raise APIError(f"csrf: HTTP {r.status_code} for {page_url}")
        form = parser.find_form(r.text, form_predicate)
        if not form:
            raise APIError(f"csrf: no matching form on {page_url}")
        token = parser.extract_csrf_from_form(form)
        if not token:
            raise APIError(f"csrf: form had no authenticity_token on {page_url}")
        return token

    def csrf_for_create(self) -> str:
        return self._csrf_from_page(
            f"{BASE}/{self.username}?tab=stars",
            parser.is_new_list_form,
        )

    def csrf_for_delete(self, slug: str) -> str:
        return self._csrf_from_page(
            f"{BASE}/stars/{self.username}/lists/{slug}",
            parser.is_delete_form,
        )

    # ---------- mutations --------------------------------------------

    def create_list(self, name: str, description: str = "", *, private: bool = False) -> bool:
        csrf = self.csrf_for_create()
        url = f"{BASE}/stars/{self.username}/lists"
        files = {
            "authenticity_token": (None, csrf),
            "user_list[name]": (None, name),
            "user_list[description]": (None, description),
            "user_list[private]": (None, "1" if private else "0"),
        }
        r = self._post(
            url,
            files=files,
            headers={
                "accept": "text/html",
                "origin": BASE,
                "referer": f"{BASE}/{self.username}?tab=stars",
                "x-requested-with": "XMLHttpRequest",
            },
            label=f"create_list {name!r}",
        )
        if r.status_code in (200, 201, 302, 303):
            return True
        err = parser.extract_first_flash_error(r.text) or ""
        raise APIError(f"create_list {name!r}: HTTP {r.status_code} — {err}")

    def delete_list(self, slug: str) -> bool:
        csrf = self.csrf_for_delete(slug)
        url = f"{BASE}/stars/{self.username}/lists/{slug}"
        r = self._post(
            url,
            data={"_method": "delete", "authenticity_token": csrf},
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "origin": BASE,
                "referer": f"{BASE}/stars/{self.username}/lists/{slug}",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
            },
            allow_redirects=False,
            label=f"delete_list {slug!r}",
        )
        if r.status_code in (200, 302, 303):
            return True
        raise APIError(f"delete_list {slug!r}: HTTP {r.status_code}")

    def assign_repo_to_lists(
        self,
        owner: str,
        repo: str,
        repo_id: int,
        list_ids: Iterable[int],
        *,
        csrf: str,
    ) -> bool:
        url = f"{BASE}/{owner}/{repo}/lists"
        fields: list[tuple[str, tuple]] = [
            ("_method", (None, "put")),
            ("authenticity_token", (None, csrf)),
            ("repository_id", (None, str(repo_id))),
            ("context", (None, "user_list_menu")),
            ("user_list_menu_dirty", (None, "1")),
        ]
        ids = list(list_ids)
        if not ids:
            fields.append(("list_ids[]", (None, "")))
        else:
            for lid in ids:
                fields.append(("list_ids[]", (None, str(lid))))
        r = self._post(
            url,
            files=fields,
            headers={
                "accept": "application/json",
                "origin": BASE,
                "referer": f"{BASE}/stars",
                "x-requested-with": "XMLHttpRequest",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            },
            label=f"assign {owner}/{repo}",
        )
        if r.status_code == 200:
            return True
        raise APIError(f"assign {owner}/{repo}: HTTP {r.status_code}")

    def find_list_id_by_name(self, list_name: str, *, probe_owner: str, probe_repo: str) -> int | None:
        """Resolve a list's numeric id by scraping any repo's list menu."""
        ctx = self.fetch_repo_context(probe_owner, probe_repo)
        target = list_name.strip().lower()
        for item in ctx.lists:
            if item["name"].strip().lower() == target:
                return item["id"]
        return None
