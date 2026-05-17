"""Singleton rich.Console with project-wide styling."""
from rich.console import Console
from rich.theme import Theme

THEME = Theme({
    "info": "cyan",
    "ok": "bold green",
    "warn": "yellow",
    "err": "bold red",
    "muted": "dim",
    "heading": "bold magenta",
    "prompt": "bold cyan",
    "kbd": "reverse",
})

console = Console(theme=THEME, highlight=False)
err_console = Console(stderr=True, theme=THEME, highlight=False)


def banner() -> None:
    console.print()
    console.print("[heading]github-manage-stars-unofficial[/heading]", justify="center")
    console.print(
        "[muted]Organise your GitHub stars into lists — unofficial UI endpoints[/muted]",
        justify="center",
    )
    console.print()
