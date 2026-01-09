"""CLI entry point for MEV Playground."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from mev_playground.config import PlaygroundConfig, DEFAULT_DATA_DIR
from mev_playground.orchestrator import Playground


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """MEV Playground - Minimal MEV integration testing environment."""
    pass


@main.command()
@click.option(
    "--relay-image",
    default=None,
    help="Override relay Docker image",
)
@click.option(
    "--builder",
    type=click.Choice(["rbuilder", "custom", "none"]),
    default="rbuilder",
    help="Builder type to use (default: rbuilder with reth-rbuilder:local image)",
)
@click.option(
    "--builder-image",
    default=None,
    help="Custom builder Docker image (when --builder=custom)",
)
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Data directory (default: {DEFAULT_DATA_DIR})",
)
def start(relay_image, builder, builder_image, data_dir):
    """Start the MEV playground."""
    try:
        playground = Playground(
            relay_image=relay_image,
            builder=builder,
            builder_image=builder_image,
            data_dir=data_dir,
        )
        playground.start()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@main.command()
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Data directory (default: {DEFAULT_DATA_DIR})",
)
def stop(data_dir):
    """Stop the MEV playground (preserve data)."""
    try:
        playground = Playground(data_dir=data_dir)
        playground.stop()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@main.command()
@click.option(
    "--artifacts-only",
    is_flag=True,
    help="Only remove artifacts, keep chain data",
)
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Data directory (default: {DEFAULT_DATA_DIR})",
)
@click.confirmation_option(
    prompt="Are you sure you want to delete all playground data?"
)
def nuke(artifacts_only, data_dir):
    """Delete all playground data and start fresh."""
    try:
        playground = Playground(data_dir=data_dir)
        playground.nuke(artifacts_only=artifacts_only)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@main.command()
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Data directory (default: {DEFAULT_DATA_DIR})",
)
def status(data_dir):
    """Show status of all components."""
    try:
        playground = Playground(data_dir=data_dir)
        component_status = playground.status()

        if not component_status:
            console.print("[yellow]No containers running[/yellow]")
            return

        table = Table(title="MEV Playground Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Health", style="green")

        for name, info in sorted(component_status.items()):
            health_style = "green" if info["health"] == "healthy" else "yellow"
            if info["health"] == "unhealthy":
                health_style = "red"

            table.add_row(
                name,
                info["status"],
                f"[{health_style}]{info['health']}[/{health_style}]",
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@main.command()
@click.argument("component")
@click.option(
    "--tail",
    default=100,
    help="Number of lines to show",
)
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Data directory (default: {DEFAULT_DATA_DIR})",
)
def logs(component, tail, data_dir):
    """Show logs from a component."""
    try:
        playground = Playground(data_dir=data_dir)
        log_output = playground.logs(component, tail)

        if log_output:
            console.print(log_output)
        else:
            console.print(f"[yellow]No logs found for {component}[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@main.command()
def info():
    """Show playground configuration and endpoints."""
    config = PlaygroundConfig()

    console.print("[bold]MEV Playground Configuration[/bold]\n")

    console.print("[cyan]Network:[/cyan]")
    console.print(f"  Chain ID:         {config.network.chain_id}")
    console.print(f"  Seconds per slot: {config.network.seconds_per_slot}")
    console.print(f"  Genesis delay:    {config.network.genesis_delay}s")

    console.print("\n[cyan]Components:[/cyan]")
    console.print(f"  Execution:  {config.execution.image}")
    console.print(f"  Consensus:  {config.consensus.image}")
    console.print(f"  Validators: {config.validators.count}")

    console.print("\n[cyan]MEV Stack:[/cyan]")
    console.print(f"  Relay:   {config.mev.relay.image}")
    console.print(f"  Builder: {config.mev.builder.image}")
    console.print(f"  Boost:   {config.mev.boost.image}")

    console.print("\n[cyan]Data Directory:[/cyan]")
    console.print(f"  {config.data_dir}")

    console.print("\n[cyan]Static IPs:[/cyan]")
    from mev_playground.config import StaticIPs
    console.print(f"  Reth:         {StaticIPs.RETH}")
    console.print(f"  Lighthouse:   {StaticIPs.LIGHTHOUSE_BN}")
    console.print(f"  MEV-Boost:    {StaticIPs.MEV_BOOST}")
    console.print(f"  Relay:        {StaticIPs.RELAY}")
    console.print(f"  rbuilder:     {StaticIPs.RBUILDER}")


if __name__ == "__main__":
    main()
