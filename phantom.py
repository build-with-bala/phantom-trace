#!/usr/bin/env python3
"""Phantom Trace - Advanced OSINT People Search Engine."""

import asyncio
import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from src.engines.async_scanner import AsyncScanner
from src.models import PersonProfile, SiteResult

console = Console()

BANNER = """[bold red]
 ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
[/bold red][bold white]           ████████╗██████╗  █████╗  ██████╗███████╗
           ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██╔════╝
              ██║   ██████╔╝███████║██║     █████╗
              ██║   ██╔══██╗██╔══██║██║     ██╔══╝
              ██║   ██║  ██║██║  ██║╚██████╗███████╗
              ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝[/bold white]
[dim]            Advanced OSINT People Search Engine[/dim]
"""


def load_sites() -> dict:
    path = Path(__file__).parent / "data" / "sites.json"
    with open(path) as f:
        return json.load(f)


def live_callback(result: SiteResult):
    if result.found:
        console.print(f"  [bold green]✓[/bold green] [cyan]{result.site:<20}[/cyan] [dim]{result.url}[/dim]")


def display_results(profile: PersonProfile):
    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_row("[bold]Target:[/bold]", f"[cyan]{profile.query}[/cyan]")
    summary.add_row("[bold]Found:[/bold]", f"[green]{profile.total_found}[/green] / {profile.total_checked} sites")
    console.print(Panel(summary, title="[bold]Summary[/bold]", border_style="cyan"))

    if profile.sites_found:
        table = Table(title="Discovered Profiles", box=box.ROUNDED, show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Platform", style="cyan", min_width=15)
        table.add_column("URL", style="blue")
        table.add_column("Category", style="yellow")

        for i, s in enumerate(sorted(profile.sites_found, key=lambda x: x.category), 1):
            table.add_row(str(i), s.site.title(), s.url, s.category)
        console.print(table)


@click.group()
def cli():
    """Phantom Trace - OSINT People Search."""
    pass


@cli.command()
@click.argument("target")
@click.option("--timeout", default=15, type=int)
@click.option("--threads", default=80, type=int)
@click.option("--proxy", default=None)
@click.option("--category", "-c", default=None)
def username(target, timeout, threads, proxy, category):
    """Search by username across 40+ platforms."""
    console.print(BANNER)
    asyncio.run(_scan(target, timeout, threads, proxy, category))


async def _scan(target, timeout, threads, proxy, category):
    sites = load_sites()
    if category:
        sites = {k: v for k, v in sites.items() if v.get("category") == category}

    console.print(f"[bold]Checking [cyan]{len(sites)}[/cyan] sites for [green]{target}[/green]...[/bold]\n")
    scanner = AsyncScanner(max_concurrent=threads, timeout=timeout, proxy=proxy)
    results = await scanner.scan_all(target, sites, callback=live_callback)

    profile = PersonProfile(query=target, query_type="username")
    profile.sites_found = [r for r in results if r.found]
    profile.sites_not_found = [r for r in results if not r.found]

    console.print()
    display_results(profile)


if __name__ == "__main__":
    cli()
