#!/usr/bin/env python3
"""Phantom Trace - Advanced OSINT People Search Engine."""

import click
from rich.console import Console
from rich.table import Table
from rich import box

from src.engines.scanner import scan_username

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


@click.group()
def cli():
    """Phantom Trace - OSINT People Search."""
    pass


@cli.command()
@click.argument("target")
@click.option("--timeout", default=10, type=int)
@click.option("--threads", default=30, type=int)
def username(target, timeout, threads):
    """Search by username across platforms."""
    console.print(BANNER)
    console.print(f"[bold cyan]Target: {target}[/bold cyan]\n")

    results = scan_username(target, max_workers=threads, timeout=timeout)
    found = [r for r in results if r.found]

    table = Table(title="Discovered Profiles", box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Platform", style="cyan", min_width=15)
    table.add_column("URL", style="blue")
    table.add_column("Category", style="yellow")

    for i, r in enumerate(sorted(found, key=lambda x: x.category), 1):
        table.add_row(str(i), r.site.title(), r.url, r.category)

    console.print(table)
    console.print(f"\n[bold green]Found on {len(found)}/{len(results)} sites[/bold green]")


if __name__ == "__main__":
    cli()
