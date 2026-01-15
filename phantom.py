#!/usr/bin/env python3
"""Phantom Trace - Advanced OSINT People Search Engine."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from src.engines.async_scanner import AsyncScanner
from src.models import PersonProfile, SiteResult
from src.modules.alias_generator import generate_aliases, generate_from_real_name
from src.modules.metadata_extractor import MetadataExtractor, calculate_confidence
from src.modules.social_graph import SocialGraphBuilder
from src.exporters.json_export import export_json
from src.exporters.html_export import export_html

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
    summary.add_row("[bold]Type:[/bold]", profile.query_type)
    summary.add_row("[bold]Found:[/bold]", f"[green]{profile.total_found}[/green] / {profile.total_checked} sites")
    summary.add_row("[bold]Confidence:[/bold]", f"[yellow]{profile.confidence_score:.0%}[/yellow]")
    if profile.real_name_guess:
        summary.add_row("[bold]Name:[/bold]", f"[green]{profile.real_name_guess}[/green]")
    if profile.locations:
        summary.add_row("[bold]Locations:[/bold]", ", ".join(set(profile.locations)))
    console.print(Panel(summary, title="[bold]Summary[/bold]", border_style="cyan"))

    if profile.sites_found:
        table = Table(title="Discovered Profiles", box=box.ROUNDED, show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Platform", style="cyan", min_width=15)
        table.add_column("URL", style="blue")
        table.add_column("Category", style="yellow")
        table.add_column("Metadata", style="dim", max_width=40)

        for i, s in enumerate(sorted(profile.sites_found, key=lambda x: x.category), 1):
            meta = "\n".join(f"{k}: {v}" for k, v in list((s.metadata or {}).items())[:3]) or "-"
            table.add_row(str(i), s.site.title(), s.url, s.category, meta)
        console.print(table)

    if profile.aliases:
        console.print(Panel(" | ".join(profile.aliases[:15]), title="[bold]Aliases[/bold]", border_style="magenta"))

    if profile.social_graph:
        console.print("\n[bold]Cross-References:[/bold]")
        for uname, sources in profile.social_graph.items():
            console.print(f"  [yellow]@{uname}[/yellow] - {', '.join(sources)}")


@click.group()
def cli():
    """Phantom Trace - OSINT People Search."""
    pass


@cli.command()
@click.argument("target")
@click.option("--output", "-o", default=None)
@click.option("--format", "-f", "fmt", default="all", type=click.Choice(["json", "html", "all"]))
@click.option("--aliases", "-a", is_flag=True, help="Also scan generated aliases")
@click.option("--category", "-c", default=None)
@click.option("--proxy", default=None)
@click.option("--timeout", default=15, type=int)
@click.option("--threads", default=80, type=int)
def username(target, output, fmt, aliases, category, proxy, timeout, threads):
    """Search by username across 40+ platforms."""
    console.print(BANNER)
    asyncio.run(_scan_username(target, output, fmt, aliases, category, proxy, timeout, threads))


@cli.command()
@click.argument("target")
@click.option("--output", "-o", default=None)
@click.option("--format", "-f", "fmt", default="all", type=click.Choice(["json", "html", "all"]))
def email(target, output, fmt):
    """Search by email address."""
    console.print(BANNER)
    asyncio.run(_scan_email(target, output, fmt))


@cli.command()
@click.argument("target")
def phone(target):
    """Search by phone number."""
    console.print(BANNER)
    asyncio.run(_scan_phone(target))


@cli.command()
@click.argument("first_name")
@click.argument("last_name")
@click.option("--birth-year", default=None, type=int)
@click.option("--output", "-o", default=None)
@click.option("--format", "-f", "fmt", default="all", type=click.Choice(["json", "html", "all"]))
def name(first_name, last_name, birth_year, output, fmt):
    """Search by real name."""
    console.print(BANNER)
    asyncio.run(_scan_name(first_name, last_name, birth_year, output, fmt))


async def _scan_username(target, output, fmt, scan_aliases, category, proxy, timeout, threads):
    sites = load_sites()
    if category:
        sites = {k: v for k, v in sites.items() if v.get("category") == category}

    console.print(f"[bold]Checking [cyan]{len(sites)}[/cyan] sites for [green]{target}[/green]...[/bold]\n")
    scanner = AsyncScanner(max_concurrent=threads, timeout=timeout, proxy=proxy)
    results = await scanner.scan_all(target, sites, callback=live_callback)

    profile = PersonProfile(query=target, query_type="username")
    profile.sites_found = [r for r in results if r.found]
    profile.sites_not_found = [r for r in results if not r.found]
    profile.aliases = generate_aliases(target)

    extractor = MetadataExtractor()
    meta = extractor.process_results(results)
    profile.real_name_guess = meta.get("probable_name")
    profile.locations = meta.get("all_locations", [])

    graph = SocialGraphBuilder()
    for r in profile.sites_found:
        graph.add_profile(target, r.site, r.url, r.api_data)
    profile.social_graph = graph.find_cross_references(results)
    profile.confidence_score = calculate_confidence(profile)

    console.print()
    display_results(profile)
    _save(profile, target, output, fmt)


async def _scan_email(target, output, fmt):
    import aiohttp
    from src.modules.email_recon import check_email
    from src.modules.breach_check import check_hibp

    async with aiohttp.ClientSession() as session:
        email_result = await check_email(target, session)
        breach_result = await check_hibp(target, session)

    table = Table(title="Email Intelligence", box=box.ROUNDED)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Email", target)
    table.add_row("Valid", str(email_result["valid"]))
    table.add_row("Provider", email_result["provider"])
    table.add_row("Gravatar", email_result.get("gravatar") or "N/A")
    table.add_row("Services", ", ".join(email_result["services"]) or "None")
    table.add_row("Breached", str(breach_result.get("breached", False)))
    console.print(table)

    prefix = target.split("@")[0]
    console.print(f"\n[bold]Also scanning username: [cyan]{prefix}[/cyan][/bold]\n")
    await _scan_username(prefix, output, fmt, False, None, None, 15, 80)


async def _scan_phone(target):
    import aiohttp
    from src.modules.phone_recon import check_phone, normalize_phone, detect_country

    async with aiohttp.ClientSession() as session:
        result = await check_phone(target, session)

    table = Table(title="Phone Intelligence", box=box.ROUNDED)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Normalized", result["number"])
    table.add_row("Country", result.get("country") or "Unknown")
    table.add_row("Services", ", ".join(result.get("services", [])) or "None")
    console.print(table)


async def _scan_name(first, last, birth_year, output, fmt):
    usernames = generate_from_real_name(first, last, birth_year)
    console.print(f"[bold]Generated {len(usernames)} username permutations[/bold]\n")

    sites = load_sites()
    scanner = AsyncScanner(max_concurrent=80, timeout=15)
    all_found = []

    for uname in usernames[:8]:
        console.print(f"[dim]--- Scanning: {uname} ---[/dim]")
        results = await scanner.scan_all(uname, sites, callback=live_callback)
        found = [r for r in results if r.found]
        if found:
            all_found.extend(found)

    profile = PersonProfile(query=f"{first} {last}", query_type="name", sites_found=all_found, real_name_guess=f"{first} {last}")
    profile.confidence_score = calculate_confidence(profile)
    display_results(profile)
    _save(profile, f"{first}_{last}", output, fmt)


def _save(profile, target, output, fmt):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = output or f"output/{target}_{ts}"
    if fmt in ("json", "all"):
        export_json(profile, f"{base}.json")
        console.print(f"\n[cyan]JSON:[/cyan] {base}.json")
    if fmt in ("html", "all"):
        export_html(profile, f"{base}.html")
        console.print(f"[cyan]HTML:[/cyan] {base}.html")


if __name__ == "__main__":
    cli()
