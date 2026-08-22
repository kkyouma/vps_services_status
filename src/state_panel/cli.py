"""CLI interface for state-panel using Typer and Rich."""

import asyncio
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from state_panel.config import load_config
from state_panel.engine import Engine
from state_panel.probes.base import CheckResult
from state_panel.server import start_server

app = typer.Typer(
    name="state-panel",
    help="Ultra-lightweight status monitor for VPS and Cloud services.",
    add_completion=False,
)
console = Console()


def _format_status_badge(status: str) -> Text:
    """Format status with color and emoji badge."""
    if status == "operational":
        return Text("🟢 Operational", style="bold green")
    if status == "degraded":
        return Text("🟡 Degraded", style="bold yellow")
    if status == "down":
        return Text("🔴 Down", style="bold red")
    return Text("⚪ Unknown", style="dim")


def _format_latency(latency_ms: float) -> Text:
    """Format latency with color coding."""
    if latency_ms == 0.0:
        return Text("-", style="dim")
    if latency_ms < 100:
        return Text(f"{latency_ms:.1f} ms", style="green")
    if latency_ms < 500:
        return Text(f"{latency_ms:.1f} ms", style="yellow")
    return Text(f"{latency_ms:.1f} ms", style="bold red")


def _render_results_table(results: list[CheckResult], overall_status: str) -> None:
    """Render check results using a Rich table."""
    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    if overall_status == "operational":
        header_text = Text(
            f"  🟢 ALL SYSTEMS OPERATIONAL  •  {now_str}  ",
            style="bold white on dark_green",
        )
    elif overall_status == "degraded":
        header_text = Text(
            f"  🟡 DEGRADED PERFORMANCE  •  {now_str}  ",
            style="bold black on dark_yellow",
        )
    else:
        header_text = Text(
            f"  🔴 MAJOR SYSTEM OUTAGE  •  {now_str}  ",
            style="bold white on dark_red",
        )

    console.print()
    console.print(Panel(header_text, expand=False, border_style="dim"))
    console.print()

    table = Table(
        title="Service Health Check Results",
        header_style="bold magenta",
        border_style="bright_black",
        expand=True,
    )
    table.add_column("Service", style="bold white", no_wrap=True)
    table.add_column("Category", style="dim")
    table.add_column("Status", justify="left")
    table.add_column("Latency", justify="right")
    table.add_column("Details", style="dim")

    for res in results:
        table.add_row(
            res.service_name,
            res.service_category,
            _format_status_badge(res.status),
            _format_latency(res.latency_ms),
            res.message,
        )

    console.print(table)
    console.print()


@app.command()
def check(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to YAML config file"
    ),
) -> None:
    """Run one-shot health check on all configured services."""
    config = load_config(config_file)
    if not config.services:
        console.print(
            "[bold yellow]Warning:[/] No services configured in services.yaml. "
            "Please create a services.yaml file."
        )
        raise typer.Exit(code=1)

    engine = Engine(config)
    with console.status("[bold green]Checking services...[/]"):
        results = asyncio.run(engine.run_checks())

    statuses = [r.status for r in results]
    overall = (
        "down"
        if any(s == "down" for s in statuses)
        else ("degraded" if any(s == "degraded" for s in statuses) else "operational")
    )

    _render_results_table(results, overall)


@app.command()
def export(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to YAML config file"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Target status.json path"
    ),
) -> None:
    """Run checks and export status.json for Cloudflare Pages."""
    config = load_config(config_file)
    engine = Engine(config)

    with console.status("[bold green]Running checks and exporting JSON...[/]"):
        results, out_path = asyncio.run(engine.run_and_export(output))

    console.print(
        f"[bold green]✓[/] Successfully checked [bold]{len(results)}[/] services "
        f"and exported data to [bold cyan]{out_path}[/]"
    )


@app.command()
def history(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to YAML config file"
    ),
    days: int = typer.Option(30, "--days", "-d", help="Number of history days"),
) -> None:
    """Display uptime and availability summary table."""
    config = load_config(config_file)
    engine = Engine(config)

    table = Table(
        title=f"Historical Uptime Summary (Past {days} Days)",
        header_style="bold cyan",
        border_style="bright_black",
        expand=True,
    )
    table.add_column("Service", style="bold white")
    table.add_column("Category", style="dim")
    table.add_column("Uptime %", justify="right")
    table.add_column("Total Checks", justify="right")

    for srv in config.services:
        hist = engine.aggregator.get_service_history(srv.id, days=days)
        uptime = hist["uptime_percentage"]
        uptime_style = (
            "bold green"
            if uptime >= 99.5
            else ("bold yellow" if uptime >= 95.0 else "bold red")
        )

        table.add_row(
            srv.name,
            srv.category,
            Text(f"{uptime:.2f} %", style=uptime_style),
            str(hist["total_checks"]),
        )

    console.print()
    console.print(table)
    console.print()


@app.command()
def seed(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to YAML config file"
    ),
    days: int = typer.Option(30, "--days", "-d", help="Number of history days to seed"),
) -> None:
    """Seed realistic mock history data for instant previewing."""
    config = load_config(config_file)
    if not config.services:
        console.print("[bold red]No services found in configuration to seed.[/]")
        raise typer.Exit(code=1)

    engine = Engine(config)
    services_meta = [{"id": s.id, "name": s.name} for s in config.services]

    with console.status(f"[bold green]Seeding {days} days of history data...[/]"):
        engine.db.seed_mock_history(services_meta, days=days)
        # Run live check and export updated status.json
        _, out_path = asyncio.run(engine.run_and_export())

    console.print(
        f"[bold green]✓[/] Successfully seeded {days} days of history into database "
        f"and generated [bold cyan]{out_path}[/]"
    )


@app.command()
def daemon(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to YAML config file"
    ),
) -> None:
    """Run continuous monitoring loop at configured intervals."""
    config = load_config(config_file)
    engine = Engine(config)
    interval = config.settings.refresh_interval_seconds

    console.print(
        f"[bold green]Starting State Panel daemon[/] (checking every {interval}s)..."
    )

    async def _loop() -> None:
        while True:
            try:
                results, out_path = await engine.run_and_export()
                now_str = datetime.now(UTC).strftime("%H:%M:%S")
                console.print(
                    f"[{now_str}] Checked {len(results)} services -> updated {out_path}"
                )
            except Exception as exc:  # noqa: BLE001
                console.print(f"[bold red]Error during check loop:[/] {exc}")
            await asyncio.sleep(interval)

    try:
        asyncio.run(_loop())
    except KeyboardInterrupt:
        console.print("\n[yellow]Daemon stopped by user.[/]")


@app.command()
def reset(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to YAML config file"
    ),
) -> None:
    """Reset the database and perform a fresh real check."""
    config = load_config(config_file)
    db_path = Path(config.settings.db_path)
    if db_path.exists():
        db_path.unlink()
        console.print(f"[bold yellow]Removed database:[/] {db_path}")

    engine = Engine(config)
    with console.status("[bold green]Performing initial real health check...[/]"):
        results, out_path = asyncio.run(engine.run_and_export())

    console.print(
        f"[bold green]✓[/] Fresh check completed for [bold]{len(results)}[/] services "
        f"and saved to [bold cyan]{out_path}[/]"
    )


@app.command()
def serve(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to YAML config file"
    ),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
) -> None:
    """Start local web server with live check API and web UI."""
    config = load_config(config_file)
    interval = config.settings.refresh_interval_seconds
    console.print(
        f"\n[bold green]⚡ State Panel Live Server running at:[/] "
        f"[bold cyan]http://{host}:{port}[/]"
    )
    console.print(f"[dim]• Real-time check API: http://{host}:{port}/api/check[/]")
    console.print(f"[dim]• Auto-check interval: {interval}s[/]\n")

    try:
        start_server(config, host=host, port=port)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user.[/]")


@app.command()
def deploy(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to YAML config file"
    ),
    project_name: str = typer.Option(
        "state-panel", "--project-name", "-p", help="Cloudflare Pages project name"
    ),
) -> None:
    """Run checks, build web bundle, and deploy to Cloudflare Pages via Wrangler."""
    config = load_config(config_file)
    engine = Engine(config)

    with console.status("[bold green]1/3 Running checks and exporting data...[/]"):
        results, out_path = asyncio.run(engine.run_and_export())

    console.print(f"[bold green]✓[/] Checked {len(results)} services -> {out_path}")

    pnpm_bin = shutil.which("pnpm") or "pnpm"
    with console.status("[bold green]2/3 Building frontend web bundle...[/]"):
        ret = subprocess.run([pnpm_bin, "build"], cwd="web", check=False)  # noqa: S603
        if ret.returncode != 0:
            console.print("[bold red]Error building web bundle with pnpm build[/]")
            raise typer.Exit(code=1)

    console.print("[bold green]✓[/] Web bundle built in web/dist")
    console.print(
        f"[bold green]3/3 Deploying to Cloudflare Pages ({project_name})...[/]"
    )
    subprocess.run(  # noqa: S603
        [
            pnpm_bin,
            "dlx",
            "wrangler",
            "pages",
            "deploy",
            "web/dist",
            f"--project-name={project_name}",
        ],
        check=False,
    )


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
