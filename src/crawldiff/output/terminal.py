"""Rich terminal output for crawldiff.

This is the viral piece — beautiful git-style diffs in the terminal.
Uses rich for panels, colored diffs, tables, and spinners.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from crawldiff.core.differ import DiffResult, PageDiff

console = Console()
err_console = Console(stderr=True)


def print_crawl_summary(url: str, page_count: int, elapsed: float) -> None:
    """Show a summary panel after a crawl completes."""
    panel = Panel(
        f"[green]{page_count}[/green] pages crawled in [cyan]{elapsed:.1f}s[/cyan]",
        title=f"[bold]{url}[/bold]",
        border_style="green",
    )
    console.print(panel)


def print_diff_result(
    diff_result: DiffResult,
    url: str,
    since: str = "",
    ai_summary: str = "",
) -> None:
    """Render a full diff result to the terminal."""
    if not diff_result.has_changes:
        console.print(Panel(
            "[dim]No changes detected[/dim]",
            title=f"[bold]{url}[/bold]",
            border_style="dim",
        ))
        return

    # Summary header
    parts: list[str] = []
    if diff_result.pages_changed:
        parts.append(f"[yellow]{len(diff_result.pages_changed)} changed[/yellow]")
    if diff_result.pages_added:
        parts.append(f"[green]{len(diff_result.pages_added)} added[/green]")
    if diff_result.pages_removed:
        parts.append(f"[red]{len(diff_result.pages_removed)} removed[/red]")
    if diff_result.pages_unchanged:
        parts.append(f"[dim]{diff_result.pages_unchanged} unchanged[/dim]")

    subtitle = f"since {since}" if since else ""
    console.print(Panel(
        ", ".join(parts),
        title=f"[bold]{url}[/bold]",
        subtitle=subtitle,
        border_style="blue",
    ))

    # Added pages
    for page in diff_result.pages_added:
        console.print(f"\n[bold green]+ NEW PAGE[/bold green]  {page.url}")

    # Removed pages
    for page in diff_result.pages_removed:
        console.print(f"\n[bold red]- REMOVED[/bold red]   {page.url}")

    # Changed pages with diffs
    for page in diff_result.pages_changed:
        console.print(f"\n[bold yellow]~ CHANGED[/bold yellow]   {page.url}")
        _print_unified_diff(page)

    # AI summary
    if ai_summary:
        console.print()
        console.print(Panel(
            ai_summary,
            title="[bold]AI Summary[/bold]",
            border_style="magenta",
            padding=(1, 2),
        ))


def _print_unified_diff(page_diff: PageDiff) -> None:
    """Render a unified diff with git-style coloring."""
    if not page_diff.unified_diff:
        return

    for line in page_diff.unified_diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            console.print(Text(line, style="bold"))
        elif line.startswith("@@"):
            console.print(Text(line, style="cyan"))
        elif line.startswith("+"):
            console.print(Text(line, style="green"))
        elif line.startswith("-"):
            console.print(Text(line, style="red"))
        else:
            console.print(Text(line, style="dim"))


def print_history_table(crawls: list[dict[str, str | int]], url: str) -> None:
    """Render crawl history as a rich table."""
    if not crawls:
        console.print(f"[dim]No crawl history for {url}[/dim]")
        return

    table = Table(title=f"Crawl History — {url}", border_style="blue")
    table.add_column("Job ID", style="cyan", no_wrap=True)
    table.add_column("Date", style="green")
    table.add_column("Pages", justify="right", style="yellow")

    for crawl in crawls:
        table.add_row(
            str(crawl["job_id"]),
            str(crawl["crawled_at"]),
            str(crawl["page_count"]),
        )

    console.print(table)


def print_config_table(config: dict[str, str]) -> None:
    """Render current config as a table."""
    table = Table(title="crawldiff configuration", border_style="blue")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for key, value in sorted(config.items()):
        table.add_row(key, value)

    console.print(table)


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    err_console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✓[/bold green] {message}")
