#!/usr/bin/env python3
"""Phantom Trace - Advanced OSINT People Search Engine with Agent Orchestration."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from src.agents.pipelines import quick_scan_pipeline, standard_pipeline, deep_pipeline, stealth_pipeline, create_context
from src.agents.base import AgentContext
from src.models import PersonProfile, SiteResult
from src.modules.alias_generator import generate_from_real_name

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
[dim]      Advanced OSINT People Search with Agent Orchestration[/dim]
"""


def display_findings(context: AgentContext):
    """Display findings from the orchestration pipeline."""
    scan_data = context.findings.get("scan_results", [])
    if scan_data:
        found = scan_data[-1].get("found", [])
        if found:
            table = Table(title=f"Discovered Profiles ({len(found)})", box=box.ROUNDED, show_lines=True)
            table.add_column("#", style="dim", width=4)
            table.add_column("Platform", style="cyan", min_width=15)
            table.add_column("URL", style="blue")
            table.add_column("Category", style="yellow")
            for i, s in enumerate(sorted(found, key=lambda x: x.get("category", "")), 1):
                table.add_row(str(i), s["site"].title(), s["url"], s.get("category", ""))
            console.print(table)

    meta_list = context.findings.get("metadata", [])
    if meta_list:
        meta = meta_list[-1]
        if meta.get("probable_name") or meta.get("all_locations"):
            info = Table(show_header=False, box=None)
            if meta.get("probable_name"):
                info.add_row("[bold]Name:[/bold]", f"[green]{meta['probable_name']}[/green]")
            if meta.get("all_locations"):
                info.add_row("[bold]Locations:[/bold]", ", ".join(set(meta["all_locations"])))
            console.print(Panel(info, title="[bold]Intelligence[/bold]", border_style="yellow"))

    ai_analysis = context.findings.get("ai_analysis", [])
    if ai_analysis:
        latest = ai_analysis[-1]
        if "analysis" in latest:
            console.print(Panel(latest["analysis"], title=f"[bold]AI Analysis ({latest.get('model', '?')})[/bold]", border_style="yellow"))

    deep = context.findings.get("deep_recon", [])
    if deep:
        console.print("\n[bold]Deep Recon Results:[/bold]")
        for alias_data in deep:
            for alias, sites in alias_data.items():
                console.print(f"  [cyan]@{alias}[/cyan] - found on {len(sites)} sites")

    reports = context.findings.get("reports", [])
    if reports:
        for r in reports:
            for fmt, path in r.items():
                console.print(f"  [bold cyan]{fmt.upper()}:[/bold cyan] {path}")


@click.group()
def cli():
    """Phantom Trace - OSINT People Search with Agent Orchestration."""
    pass


@cli.command()
@click.argument("target")
@click.option("--mode", "-m", default="standard", type=click.Choice(["quick", "standard", "deep", "stealth"]))
@click.option("--proxy", default=None)
def username(target, mode, proxy):
    """Search by username with agent orchestration."""
    console.print(BANNER)
    console.print(f"[bold]Mode: [cyan]{mode}[/cyan] | Target: [green]{target}[/green][/bold]\n")
    asyncio.run(_run_pipeline(target, "username", mode))


@cli.command()
@click.argument("target")
@click.option("--mode", "-m", default="standard", type=click.Choice(["quick", "standard", "deep", "stealth"]))
def email(target, mode):
    """Search by email address."""
    console.print(BANNER)
    prefix = target.split("@")[0]
    console.print(f"[bold]Email: [green]{target}[/green] → scanning as username: [cyan]{prefix}[/cyan][/bold]\n")
    asyncio.run(_run_pipeline(prefix, "email", mode))


@cli.command()
@click.argument("first_name")
@click.argument("last_name")
@click.option("--birth-year", default=None, type=int)
@click.option("--mode", "-m", default="standard", type=click.Choice(["quick", "standard", "deep", "stealth"]))
def name(first_name, last_name, birth_year, mode):
    """Search by real name (generates username permutations)."""
    console.print(BANNER)
    usernames = generate_from_real_name(first_name, last_name, birth_year)
    console.print(f"[bold]Name: [green]{first_name} {last_name}[/green] → {len(usernames)} permutations[/bold]\n")

    async def _run():
        for uname in usernames[:5]:
            console.print(f"\n[bold magenta]━━━ Scanning: {uname} ━━━[/bold magenta]")
            await _run_pipeline(uname, "name", mode)

    asyncio.run(_run())


@cli.command()
def providers():
    """Check available AI providers."""
    console.print(BANNER)
    asyncio.run(_check_providers())


async def _run_pipeline(target: str, target_type: str, mode: str):
    """Execute the selected pipeline."""
    context = create_context(target, target_type)

    pipelines = {"quick": quick_scan_pipeline, "standard": standard_pipeline, "deep": deep_pipeline, "stealth": stealth_pipeline}
    pipeline = pipelines[mode]()

    result = await pipeline.execute(context)

    console.print()
    display_findings(result.context)

    if not result.success:
        failed = ", ".join(result.stages_failed)
        console.print(f"\n[yellow]Warning: Some stages failed: {failed}[/yellow]")


async def _check_providers():
    """Check and display available AI providers."""
    from src.ai.router import create_default_router
    router = create_default_router()
    status = await router.check_availability()

    table = Table(title="AI Provider Status", box=box.ROUNDED)
    table.add_column("Provider", style="cyan")
    table.add_column("Status")

    for name, available in status.items():
        s = "[bold green]Available[/bold green]" if available else "[red]Unavailable[/red]"
        table.add_row(name, s)

    console.print(table)


if __name__ == "__main__":
    cli()
