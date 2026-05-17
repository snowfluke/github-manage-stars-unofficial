"""Click-based CLI with an interactive menu when invoked with no subcommand."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.table import Table

from . import categorize as cat_module
from . import config, credentials, fetch as fetch_module, orchestrator, presets
from .api import APIError, StarsAPI
from .categorize import Category, Repo
from .console import banner, console
from .state import State
from .validators import (
    MAX_LIST_NAME_LENGTH,
    MAX_LISTS_PER_ACCOUNT,
    validate_category_set,
    validate_list_name,
)


# =============================================================
# helpers
# =============================================================

def _exit_with(message: str, code: int = 1) -> None:
    console.print(f"[err]{message}[/err]")
    sys.exit(code)


def _require_credentials() -> credentials.Credentials:
    creds = credentials.load()
    if not creds:
        _exit_with(
            "No credentials set. Run [kbd]ghstars setup[/kbd] first "
            "(or pick \"Setup credentials\" from the menu).",
        )
    missing = credentials.missing_required(creds.cookies)
    if missing:
        _exit_with(f"Stored credentials are missing required cookies: {missing}.")
    return creds


def _make_api(creds: credentials.Credentials, *, username: str | None = None) -> StarsAPI:
    settings = config.load_settings()
    user = username or creds.username
    if not user:
        user = Prompt.ask("[prompt]GitHub username[/prompt]").strip()
    return StarsAPI(user, creds.cookies, settings)


def _load_categories_path_or_defaults(path: Path | None) -> list[Category]:
    if path:
        cats = cat_module.load_categories_json(path)
    else:
        cats = list(presets.DEFAULT_CATEGORIES)
    issues = validate_category_set([{
        "name": c.name,
        "description": c.description,
        "patterns": c.patterns,
    } for c in cats])
    if issues:
        for it in issues:
            console.print(f"[err]category error:[/err] {it}")
        sys.exit(1)
    return cats


def _confirm_destructive(prompt: str, *, allow_yes_flag: bool = False) -> bool:
    if allow_yes_flag and os.environ.get("GHSTARS_YES") == "1":
        return True
    return Confirm.ask(f"[warn]{prompt}[/warn]", default=False)


def _format_existing_lists(lists) -> Table:
    tbl = Table(title=f"Existing star lists ({len(lists)})", show_lines=False)
    tbl.add_column("#", justify="right", style="muted")
    tbl.add_column("slug", style="info")
    tbl.add_column("name")
    for i, l in enumerate(lists, 1):
        tbl.add_row(str(i), l.slug, l.name)
    return tbl


def _bucket_summary(buckets: dict[str, list[Repo]]) -> Table:
    tbl = Table(title="Categorisation plan", show_lines=False)
    tbl.add_column("#", justify="right", style="muted")
    tbl.add_column("list", style="info")
    tbl.add_column("count", justify="right")
    for i, (name, items) in enumerate(
        sorted(buckets.items(), key=lambda x: -len(x[1])), 1
    ):
        tbl.add_row(str(i), name, str(len(items)))
    tbl.add_row("", "[bold]TOTAL[/bold]", f"[bold]{sum(len(v) for v in buckets.values())}[/bold]")
    return tbl


# =============================================================
# Command: setup
# =============================================================

SETUP_INSTRUCTIONS = """\
[heading]Setup credentials[/heading]

This tool authenticates against GitHub using your browser session cookies.
[err]Treat these cookies like a password[/err] — anyone who has them can
fully impersonate your account.

How to get them:
 1. Sign in to https://github.com in your browser (Chrome / Brave / Firefox).
 2. Open DevTools → [kbd]Application[/kbd] tab (or [kbd]Storage[/kbd] in Firefox).
 3. Under [kbd]Cookies → https://github.com[/kbd], copy the values of:
       • [info]user_session[/info]                      (required)
       • [info]__Host-user_session_same_site[/info]     (recommended)
       • [info]_gh_sess[/info]                          (required)
       • [info]dotcom_user[/info]                       (recommended — your username)
 4. Paste them when prompted.

[muted]Alternatively, copy a request from the Network tab as cURL and paste the
whole cookie string when prompted — the parser will extract what it needs.[/muted]
"""


def _interactive_setup() -> None:
    console.print(Panel.fit(SETUP_INSTRUCTIONS, border_style="muted"))
    mode = Prompt.ask(
        "[prompt]Input mode[/prompt]",
        choices=["paste", "fields"],
        default="paste",
    )
    cookies: dict[str, str] = {}
    if mode == "paste":
        console.print(
            "[info]Paste a full Cookie header or curl -b argument, "
            "then end input with a single line containing only 'EOF'.[/info]"
        )
        buf: list[str] = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line.strip() == "EOF":
                break
            buf.append(line)
        raw = "\n".join(buf).strip()
        cookies = credentials.parse_curl_cookie_header(raw)
    else:
        for cookie_name in credentials.REQUIRED_COOKIES + credentials.OPTIONAL_COOKIES:
            v = Prompt.ask(f"[prompt]{cookie_name}[/prompt] (empty to skip)", default="")
            if v.strip():
                cookies[cookie_name] = v.strip()

    missing = credentials.missing_required(cookies)
    if missing:
        _exit_with(f"Missing required cookies: {missing}.")

    username = cookies.get("dotcom_user") or Prompt.ask("[prompt]GitHub username[/prompt]")
    cookies["dotcom_user"] = username

    creds = credentials.Credentials(cookies=cookies)
    path = credentials.save(creds)
    console.print(f"[ok]Saved to {path}[/ok] (chmod 600)")

    # Verification
    try:
        api = _make_api(creds, username=username)
        title = api.whoami()
        console.print(f"[ok]Authenticated:[/ok] {title}")
    except APIError as e:
        console.print(
            f"[err]Verification failed: {e}[/err]\n"
            "Credentials are saved but may be invalid. Re-run setup or check your cookies."
        )


@click.command()
def setup() -> None:
    """Set up your GitHub session cookies for API access."""
    _interactive_setup()


# =============================================================
# Command: fetch
# =============================================================

@click.command()
@click.option(
    "--username",
    default=None,
    help="GitHub username. Defaults to the dotcom_user cookie.",
)
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output path. Defaults to ./stars-<username>-<timestamp>.json",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "jsonl"]),
    default="json",
    help="json (pretty array, AI-ready) or jsonl (one repo per line).",
)
def fetch(username: Optional[str], out: Optional[Path], fmt: str) -> None:
    """Dump your starred repositories to a JSON file (great input for an LLM)."""
    creds = credentials.load()
    user = username or (creds.username if creds else None)
    if not user:
        user = Prompt.ask("[prompt]GitHub username[/prompt]").strip()
    if not user:
        _exit_with("No username provided.")

    if out is None:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = Path.cwd() / f"stars-{user}-{ts}.{fmt}"

    console.print(f"[info]Fetching stars for[/info] [bold]{user}[/bold]...")
    repos = fetch_module.fetch_starred(
        user,
        progress=lambda n, _t: console.print(f"  {n} fetched so far..."),
    )
    if fmt == "jsonl":
        fetch_module.dump_jsonl(repos, out)
    else:
        fetch_module.dump_json_array(repos, out)
    console.print(f"[ok]Wrote {len(repos)} repos to[/ok] {out}")


# =============================================================
# Command: list-lists
# =============================================================

@click.command(name="list-lists")
def list_lists_cmd() -> None:
    """Show the star lists currently on your account."""
    creds = _require_credentials()
    api = _make_api(creds)
    try:
        lists = api.list_lists()
    except APIError as e:
        _exit_with(str(e))
    console.print(_format_existing_lists(lists))


# =============================================================
# Command: delete-lists
# =============================================================

@click.command(name="delete-lists")
@click.option("--all", "wipe_all", is_flag=True, help="Delete ALL existing lists.")
@click.option(
    "--slugs",
    default=None,
    help="Comma-separated slugs to delete. Mutually exclusive with --all.",
)
def delete_lists_cmd(wipe_all: bool, slugs: Optional[str]) -> None:
    """Delete one, some, or all of your star lists. Irreversible."""
    if wipe_all == bool(slugs):
        _exit_with("Pass exactly one of --all or --slugs=a,b,c.")

    creds = _require_credentials()
    api = _make_api(creds)
    try:
        existing = api.list_lists()
    except APIError as e:
        _exit_with(str(e))

    if wipe_all:
        targets = [l.slug for l in existing]
    else:
        wanted = {s.strip() for s in (slugs or "").split(",") if s.strip()}
        valid_slugs = {l.slug for l in existing}
        unknown = wanted - valid_slugs
        if unknown:
            _exit_with(f"Unknown slugs: {sorted(unknown)}")
        targets = sorted(wanted)

    if not targets:
        console.print("[muted]Nothing to delete.[/muted]")
        return

    console.print(_format_existing_lists([l for l in existing if l.slug in targets]))
    if not _confirm_destructive(
        f"Delete {len(targets)} list(s)? This cannot be undone.",
        allow_yes_flag=True,
    ):
        console.print("[muted]Aborted.[/muted]")
        return

    result = orchestrator.delete_lists(
        api,
        targets,
        on_event=lambda msg: console.print(f"  [info]·[/info] {msg}"),
    )
    console.print(
        f"[ok]Deleted {len(result.deleted)}[/ok], "
        f"[err]failed {len(result.failed)}[/err]"
    )


# =============================================================
# Command: apply (delete-all + create + assign)
# =============================================================

@click.command()
@click.option(
    "--stars",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to a stars JSON or JSONL file (output of `ghstars fetch`).",
)
@click.option(
    "--categories",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Custom categories JSON. Omit to use built-in 32 defaults.",
)
@click.option(
    "--wipe-existing/--no-wipe-existing",
    default=False,
    help="Delete all existing lists before creating new ones (DESTRUCTIVE).",
)
@click.option(
    "--phase",
    type=click.Choice(["plan", "create", "assign", "all"]),
    default="all",
    help="Which phase to run. `plan` is a dry run.",
)
def apply(
    stars: Path,
    categories: Optional[Path],
    wipe_existing: bool,
    phase: str,
) -> None:
    """End-to-end: categorise → optionally wipe → create lists → assign repos."""
    # 1. Load repos and categories (works without credentials — `plan` is offline)
    cats = _load_categories_path_or_defaults(categories)
    if stars.suffix == ".jsonl":
        repos = cat_module.load_stars_jsonl(stars)
    else:
        repos = [Repo.from_dict(d) for d in json.loads(stars.read_text())]
    console.print(f"[info]Loaded[/info] {len(repos)} repos, {len(cats)} categories.")

    buckets = orchestrator.plan_buckets(repos, cats)
    console.print(_bucket_summary(buckets))

    if phase == "plan":
        return

    # Phases other than plan touch GitHub, so credentials are required from here on.
    creds = _require_credentials()
    api = _make_api(creds)

    # 2. Optional wipe
    if wipe_existing:
        existing = api.list_lists()
        if existing:
            console.print(_format_existing_lists(existing))
            if not _confirm_destructive(
                f"About to DELETE {len(existing)} existing list(s). Continue?",
                allow_yes_flag=True,
            ):
                _exit_with("Aborted by user.", code=0)
            orchestrator.delete_lists(
                api,
                [l.slug for l in existing],
                on_event=lambda m: console.print(f"  [info]·[/info] {m}"),
            )

    state = State.load(api.username)

    # 3. Create lists
    if phase in {"create", "all"}:
        if repos:
            probe_owner, probe_repo = repos[0].name.split("/", 1)
        else:
            _exit_with("No repos in stars file — cannot probe for list IDs.")
        create_res = orchestrator.create_lists(
            api,
            state,
            cats,
            probe_owner=probe_owner,
            probe_repo=probe_repo,
            on_event=lambda m: console.print(f"  [info]·[/info] {m}"),
        )
        console.print(
            f"[ok]Created {len(create_res.created)}[/ok], "
            f"[muted]skipped {len(create_res.skipped)}[/muted], "
            f"[err]failed {len(create_res.failed)}[/err]"
        )
        if create_res.failed:
            for name, reason in create_res.failed:
                console.print(f"  [err]✗[/err] {name}: {reason}")
            if phase == "all":
                _exit_with("Halting before assign because list creation failed.")

    # 4. Assign repos
    if phase in {"assign", "all"}:
        if not state.created_lists:
            _exit_with("State has no created lists. Run `apply --phase create` first.")
        console.print(f"[info]Assigning[/info] {len(repos)} repos...")
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            SpinnerColumn,
            TextColumn,
            TimeRemainingColumn,
        )
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
        )
        with progress:
            t = progress.add_task("assigning", total=sum(len(v) for v in buckets.values()))
            assign_res = orchestrator.assign_repos(
                api,
                state,
                buckets,
                on_event=lambda _m: progress.update(t, advance=1),
            )
        console.print(
            f"[ok]Assigned {assign_res.assigned}[/ok], "
            f"[muted]skipped {assign_res.skipped}[/muted], "
            f"[err]failed {len(assign_res.failed)}[/err]"
        )
        if assign_res.failed:
            for name, reason in assign_res.failed[:10]:
                console.print(f"  [err]✗[/err] {name}: {reason}")


# =============================================================
# Command: settings
# =============================================================

@click.command()
def settings() -> None:
    """View or edit jitter / retry settings."""
    s = config.load_settings()
    tbl = Table(title="Current settings", show_lines=False)
    tbl.add_column("key", style="info")
    tbl.add_column("value")
    for k, v in asdict(s).items():
        tbl.add_row(k, str(v))
    console.print(tbl)

    if not Confirm.ask("[prompt]Edit?[/prompt]", default=False):
        return

    console.print(
        "[warn]Be careful with jitter — values below 1.0s risk being flagged "
        "by GitHub.[/warn]"
    )
    s.jitter_min = FloatPrompt.ask("jitter_min (seconds)", default=s.jitter_min)
    s.jitter_max = FloatPrompt.ask("jitter_max (seconds)", default=s.jitter_max)
    s.phase_pause_min = FloatPrompt.ask("phase_pause_min", default=s.phase_pause_min)
    s.phase_pause_max = FloatPrompt.ask("phase_pause_max", default=s.phase_pause_max)
    s.retry_attempts = IntPrompt.ask("retry_attempts", default=s.retry_attempts)
    s.retry_base_seconds = FloatPrompt.ask(
        "retry_base_seconds (exponential backoff base)", default=s.retry_base_seconds
    )

    issues = s.validate()
    if issues:
        for it in issues:
            console.print(f"[warn]warning: {it}[/warn]")
        if not Confirm.ask("[prompt]Save anyway?[/prompt]", default=False):
            return
    config.save_settings(s)
    console.print(f"[ok]Saved to {config.SETTINGS_FILE}[/ok]")


# =============================================================
# Command: clear-credentials
# =============================================================

@click.command(name="clear-credentials")
def clear_credentials_cmd() -> None:
    """Remove stored credentials from this machine."""
    if not credentials.load():
        console.print("[muted]No credentials stored.[/muted]")
        return
    if not _confirm_destructive("Remove stored credentials?", allow_yes_flag=True):
        console.print("[muted]Aborted.[/muted]")
        return
    credentials.clear()
    console.print("[ok]Credentials cleared.[/ok]")
    console.print(
        "[warn]Reminder:[/warn] also revoke the matching browser session at "
        "https://github.com/settings/sessions if you suspect cookie exposure."
    )


# =============================================================
# Command: status
# =============================================================

@click.command()
def status() -> None:
    """Show what the tool knows about — credentials, settings, current state."""
    creds = credentials.load()
    s = config.load_settings()

    cred_tbl = Table(title="Credentials", show_lines=False)
    cred_tbl.add_column("key", style="info")
    cred_tbl.add_column("value")
    cred_tbl.add_row("file", str(config.CREDENTIALS_FILE))
    cred_tbl.add_row("present", "yes" if creds else "[err]no[/err]")
    if creds:
        cred_tbl.add_row("username", creds.username or "(unknown)")
        cred_tbl.add_row("cookies", ", ".join(sorted(creds.cookies)))
    console.print(cred_tbl)

    if creds and creds.username:
        st = State.load(creds.username)
        st_tbl = Table(title="Resume state", show_lines=False)
        st_tbl.add_column("key", style="info")
        st_tbl.add_column("value")
        st_tbl.add_row("file", str(st.path))
        st_tbl.add_row("created lists", str(len(st.created_lists)))
        st_tbl.add_row("assigned repos", str(len(st.assigned_repos)))
        console.print(st_tbl)

    set_tbl = Table(title="Settings", show_lines=False)
    set_tbl.add_column("key", style="info")
    set_tbl.add_column("value")
    for k, v in asdict(s).items():
        set_tbl.add_row(k, str(v))
    console.print(set_tbl)


# =============================================================
# Interactive menu
# =============================================================

MENU_OPTIONS = [
    ("Setup credentials", "setup"),
    ("Fetch & dump my starred repos", "fetch"),
    ("Show current GitHub star lists", "list-lists"),
    ("Apply management (categorise + create + assign)", "apply"),
    ("Delete star lists (single / bulk / all)", "delete-lists"),
    ("Edit settings (jitter, retries)", "settings"),
    ("Show status", "status"),
    ("Clear credentials", "clear-credentials"),
    ("Quit", "quit"),
]


def _show_menu() -> str:
    console.print()
    tbl = Table(show_header=False, box=None, padding=(0, 2))
    tbl.add_column(style="kbd", justify="right")
    tbl.add_column()
    for i, (label, _) in enumerate(MENU_OPTIONS, 1):
        tbl.add_row(str(i), label)
    console.print(tbl)
    raw = Prompt.ask(
        "[prompt]Pick an action[/prompt]",
        choices=[str(i) for i in range(1, len(MENU_OPTIONS) + 1)],
        default="1",
    )
    return MENU_OPTIONS[int(raw) - 1][1]


def _interactive_apply() -> None:
    creds = _require_credentials()
    api = _make_api(creds)

    stars_path = Prompt.ask(
        "[prompt]Path to stars JSON / JSONL[/prompt] "
        "([muted]leave empty to fetch fresh[/muted])",
        default="",
    ).strip()
    if not stars_path:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        stars_out = Path.cwd() / f"stars-{api.username}-{ts}.json"
        console.print("[info]Fetching stars first...[/info]")
        repos = fetch_module.fetch_starred(api.username)
        fetch_module.dump_json_array(repos, stars_out)
        console.print(f"[ok]Wrote {len(repos)} repos to[/ok] {stars_out}")
        stars_path = str(stars_out)

    categories_path_str = Prompt.ask(
        "[prompt]Custom categories JSON[/prompt] "
        "([muted]empty = use built-in 32 defaults[/muted])",
        default="",
    ).strip()
    categories_path = Path(categories_path_str) if categories_path_str else None

    wipe = Confirm.ask(
        "[warn]Delete ALL existing lists before creating new ones?[/warn]",
        default=False,
    )

    # Hand off to the same click command — easiest way to reuse
    ctx = click.Context(apply)
    ctx.invoke(
        apply,
        stars=Path(stars_path),
        categories=categories_path,
        wipe_existing=wipe,
        phase="all",
    )


def _interactive_delete() -> None:
    creds = _require_credentials()
    api = _make_api(creds)
    try:
        existing = api.list_lists()
    except APIError as e:
        _exit_with(str(e))
    if not existing:
        console.print("[muted]No lists to delete.[/muted]")
        return

    console.print(_format_existing_lists(existing))
    choice = Prompt.ask(
        "[prompt]Delete[/prompt]",
        choices=["all", "some", "cancel"],
        default="cancel",
    )
    if choice == "cancel":
        return
    if choice == "all":
        if not _confirm_destructive(
            f"Delete ALL {len(existing)} lists? Irreversible.",
            allow_yes_flag=True,
        ):
            return
        targets = [l.slug for l in existing]
    else:
        raw = Prompt.ask(
            "[prompt]Slugs to delete[/prompt] "
            "(comma-separated, e.g. [info]old-list,trash[/info])"
        )
        wanted = {s.strip() for s in raw.split(",") if s.strip()}
        valid = {l.slug for l in existing}
        unknown = wanted - valid
        if unknown:
            console.print(f"[err]Unknown slugs:[/err] {sorted(unknown)}")
            return
        targets = sorted(wanted)
        if not _confirm_destructive(f"Delete {len(targets)} list(s)?", allow_yes_flag=True):
            return

    res = orchestrator.delete_lists(
        api,
        targets,
        on_event=lambda m: console.print(f"  [info]·[/info] {m}"),
    )
    console.print(
        f"[ok]Deleted {len(res.deleted)}[/ok], "
        f"[err]failed {len(res.failed)}[/err]"
    )


@click.command(name="menu")
def menu_cmd() -> None:
    """Run the interactive menu (default when ghstars is called with no args)."""
    banner()
    while True:
        try:
            action = _show_menu()
        except (KeyboardInterrupt, EOFError):
            console.print()
            return
        if action == "quit":
            return
        try:
            if action == "setup":
                _interactive_setup()
            elif action == "fetch":
                ctx = click.Context(fetch)
                ctx.invoke(fetch, username=None, out=None, fmt="json")
            elif action == "list-lists":
                ctx = click.Context(list_lists_cmd)
                ctx.invoke(list_lists_cmd)
            elif action == "apply":
                _interactive_apply()
            elif action == "delete-lists":
                _interactive_delete()
            elif action == "settings":
                ctx = click.Context(settings)
                ctx.invoke(settings)
            elif action == "status":
                ctx = click.Context(status)
                ctx.invoke(status)
            elif action == "clear-credentials":
                ctx = click.Context(clear_credentials_cmd)
                ctx.invoke(clear_credentials_cmd)
        except click.exceptions.Exit:
            # subcommand called sys.exit; keep menu alive
            pass
        except KeyboardInterrupt:
            console.print("\n[muted]Cancelled[/muted]")


# =============================================================
# Click group
# =============================================================

@click.group(invoke_without_command=True)
@click.version_option(message="%(prog)s %(version)s")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Manage your GitHub star lists via unofficial UI endpoints.

    Run with no subcommand for an interactive menu.
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(menu_cmd)


main.add_command(setup)
main.add_command(fetch)
main.add_command(list_lists_cmd)
main.add_command(delete_lists_cmd)
main.add_command(apply)
main.add_command(settings)
main.add_command(clear_credentials_cmd)
main.add_command(status)
main.add_command(menu_cmd)


if __name__ == "__main__":
    main()
