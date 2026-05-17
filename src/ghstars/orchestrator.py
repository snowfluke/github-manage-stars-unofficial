"""Higher-level workflows that combine API + state + categorisation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .api import APIError, StarsAPI
from .categorize import Category, Repo, categorize
from .parser import ListInfo
from .state import State


@dataclass
class CreateResult:
    created: list[tuple[str, int]]   # (list name, list id)
    skipped: list[str]               # already in state, not recreated
    failed: list[tuple[str, str]]    # (list name, reason)


def create_lists(
    api: StarsAPI,
    state: State,
    categories: list[Category],
    *,
    probe_owner: str,
    probe_repo: str,
    on_event: Callable[[str], None] | None = None,
) -> CreateResult:
    """Create every category as a list, recording the resulting IDs in state.

    A probe repo is needed because GitHub's UI does not return the new list's ID
    on the create response — we resolve it by scraping any starred repo's menu.
    """
    res = CreateResult([], [], [])
    for cat in categories:
        if cat.name in state.created_lists:
            res.skipped.append(cat.name)
            if on_event:
                on_event(f"skip {cat.name!r} (already created)")
            continue
        try:
            api.create_list(cat.name, cat.description)
        except APIError as e:
            res.failed.append((cat.name, str(e)))
            if on_event:
                on_event(f"FAIL create {cat.name!r}: {e}")
            continue
        api.jitter()

        list_id = api.find_list_id_by_name(
            cat.name,
            probe_owner=probe_owner,
            probe_repo=probe_repo,
        )
        if not list_id:
            res.failed.append((cat.name, "could not resolve numeric id after create"))
            if on_event:
                on_event(f"FAIL resolve id for {cat.name!r}")
            continue
        state.created_lists[cat.name] = list_id
        state.save()
        res.created.append((cat.name, list_id))
        if on_event:
            on_event(f"created {cat.name!r} id={list_id}")
        api.jitter()
    return res


@dataclass
class DeleteResult:
    deleted: list[str]
    failed: list[tuple[str, str]]


def delete_lists(
    api: StarsAPI,
    slugs: Iterable[str],
    *,
    on_event: Callable[[str], None] | None = None,
) -> DeleteResult:
    res = DeleteResult([], [])
    for slug in slugs:
        try:
            api.delete_list(slug)
        except APIError as e:
            res.failed.append((slug, str(e)))
            if on_event:
                on_event(f"FAIL delete {slug}: {e}")
            continue
        res.deleted.append(slug)
        if on_event:
            on_event(f"deleted {slug}")
        api.jitter()
    return res


@dataclass
class AssignResult:
    assigned: int
    skipped: int
    failed: list[tuple[str, str]]


def assign_repos(
    api: StarsAPI,
    state: State,
    buckets: dict[str, list[Repo]],
    *,
    on_event: Callable[[str], None] | None = None,
    fail_fast_after: int | None = 10,
) -> AssignResult:
    """For each repo, set its list memberships to exactly the bucket it belongs to."""
    res = AssignResult(0, 0, [])

    # Flatten into a stable (list_name, repo) work queue
    work: list[tuple[str, Repo]] = []
    for list_name, repos in buckets.items():
        for r in repos:
            work.append((list_name, r))

    for list_name, repo in work:
        if repo.name in state.assigned_repos:
            res.skipped += 1
            continue
        list_id = state.created_lists.get(list_name)
        if not list_id:
            res.failed.append((repo.name, f"no list_id for {list_name!r}"))
            continue
        owner, name_only = repo.name.split("/", 1)
        try:
            ctx = api.fetch_repo_context(owner, name_only)
            if not ctx.csrf:
                raise APIError("missing CSRF in repo list fragment")
            api.assign_repo_to_lists(owner, name_only, repo.id, [list_id], csrf=ctx.csrf)
        except APIError as e:
            res.failed.append((repo.name, str(e)))
            if on_event:
                on_event(f"FAIL {repo.name}: {e}")
            api.jitter()
            if fail_fast_after is not None and len(res.failed) >= fail_fast_after:
                break
            continue
        res.assigned += 1
        state.assigned_repos.add(repo.name)
        state.save()
        if on_event:
            on_event(f"{repo.name} -> {list_name}")
        api.jitter()
    return res


def fetch_existing_lists(api: StarsAPI) -> list[ListInfo]:
    return api.list_lists()


def plan_buckets(repos: list[Repo], categories: list[Category]) -> dict[str, list[Repo]]:
    return categorize(repos, categories)
