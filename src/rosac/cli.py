from __future__ import annotations
from pathlib import Path
from typing import Annotated
import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import RosacConfig, TargetConfig, BUILTIN_PROFILES
from .models import TargetContext

app = typer.Typer(
    name="rosac",
    help="RouterOS Artifact Collector -- forensic triage for Mikrotik RouterOS devices.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"rosac {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[bool, typer.Option("--version", "-v", callback=version_callback, is_eager=True)] = False,
):
    pass


@app.command()
def collect(
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target router IP or hostname")] = None,
    targets_file: Annotated[Path | None, typer.Option("--targets", help="File with one target per line")] = None,
    username: Annotated[str, typer.Option("--user", "-u", help="SSH/API username")] = "admin",
    keyfile: Annotated[str | None, typer.Option("--key", "-k", help="Path to SSH private key")] = None,
    password: Annotated[bool, typer.Option("--password", "-p", help="Prompt for password")] = False,
    transport: Annotated[str, typer.Option(help="Transport: ssh or api")] = "ssh",
    api_port: Annotated[int, typer.Option(help="RouterOS API port")] = 8728,
    api_tls: Annotated[bool, typer.Option(help="Use TLS for RouterOS API")] = False,
    profile: Annotated[str | None, typer.Option("--profile", help="Named collection profile")] = None,
    categories: Annotated[str | None, typer.Option("--categories", "-c", help="Comma-separated categories to collect")] = None,
    analyze: Annotated[bool, typer.Option("--analyze", "-a", help="Run analysis after collection")] = False,
    workers: Annotated[int, typer.Option("--workers", "-w", help="Max concurrent targets")] = 5,
    output_dir: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("output"),
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be collected, do not connect")] = False,
):
    """Collect forensic artifacts from one or more RouterOS devices."""
    cfg = RosacConfig.load()

    # Validate at least one target
    if not target and not targets_file:
        console.print("[red]Error:[/red] Provide --target or --targets")
        raise typer.Exit(1)

    # Resolve targets
    target_hosts: list[str] = []
    if target:
        target_hosts.append(target)
    if targets_file:
        if not targets_file.exists():
            console.print(f"[red]Error:[/red] Targets file not found: {targets_file}")
            raise typer.Exit(1)
        target_hosts.extend(l.strip() for l in targets_file.read_text().splitlines() if l.strip() and not l.startswith("#"))

    # Resolve password
    pwd: str | None = None
    if password:
        pwd = typer.prompt("Password", hide_input=True)

    # Resolve profile
    active_profile = None
    if profile:
        active_profile = cfg.get_profile(profile)
        if not active_profile:
            console.print(f"[red]Error:[/red] Unknown profile '{profile}'. Available: {', '.join(list(BUILTIN_PROFILES.keys()) + list(cfg.profiles.keys()))}")
            raise typer.Exit(1)

    # Resolve categories
    cat_list: list[str] = []
    if categories:
        cat_list = [c.strip() for c in categories.split(",")]
    elif active_profile:
        cat_list = active_profile.categories

    if dry_run:
        _show_dry_run(target_hosts, username, transport, cat_list, analyze, workers, output_dir, active_profile)
        return

    # Phase 2+ will implement actual collection here
    console.print("[yellow]Collection not yet implemented -- use --dry-run to preview.[/yellow]")


def _show_dry_run(targets, username, transport, categories, analyze, workers, output_dir, profile):
    console.print("\n[bold cyan]rosac -- Dry Run[/bold cyan]\n")

    t = Table(show_header=True, header_style="bold")
    t.add_column("Setting")
    t.add_column("Value")
    t.add_row("Targets", str(len(targets)))
    for i, host in enumerate(targets):
        t.add_row(f"  target[{i}]", host)
    t.add_row("Username", username)
    t.add_row("Transport", transport)
    t.add_row("Categories", ", ".join(categories) if categories else "all")
    t.add_row("Analyze", str(analyze))
    t.add_row("Workers", str(workers))
    t.add_row("Output dir", str(output_dir))
    if profile:
        t.add_row("Profile", profile.description)
    console.print(t)


@app.command()
def analyze(
    input_dir: Annotated[Path, typer.Option("--input", "-i", help="Path to collected output directory")],
    severity: Annotated[str | None, typer.Option("--severity", "-s", help="Filter: critical,high,medium,info")] = None,
):
    """Analyze previously collected artifacts (offline mode)."""
    if not input_dir.exists():
        console.print(f"[red]Error:[/red] Input directory not found: {input_dir}")
        raise typer.Exit(1)
    # Phase 4 will implement analysis here
    console.print("[yellow]Offline analysis not yet implemented.[/yellow]")


if __name__ == "__main__":
    app()
