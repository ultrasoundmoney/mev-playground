"""CLI entry point for MEV Playground."""

import click
import logging
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from web3 import Web3

from mev_playground.config import DEFAULT_DATA_DIR, get_rbuilder_image
from mev_playground.orchestrator import Playground, NUM_VALIDATORS

# Default rbuilder extra_data (🦇🔊 = "ultrasound")
DEFAULT_EXTRA_DATA = "🦇🔊"


console = Console()


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.version_option(version="0.1.0")
@click.option(
    "--debug",
    is_flag=True,
    envvar="MEV_PLAYGROUND_DEBUG",
    help="Enable debug logging",
)
@click.pass_context
def main(ctx, debug):
    """MEV Playground - Minimal MEV integration testing environment."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    setup_logging(debug)


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
    help="Builder type to use (default: rbuilder with ghcr.io/flashbots/rbuilder image)",
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
@click.option(
    "--no-contender",
    is_flag=True,
    help="Skip starting Contender transaction spammer",
)
@click.option(
    "--tps",
    default=20,
    help="Contender transactions per second (default: 20)",
)
def start(relay_image, builder, builder_image, data_dir, no_contender, tps):
    """Start the MEV playground."""
    try:
        playground = Playground(
            relay_image=relay_image,
            builder=builder,
            builder_image=builder_image,
            data_dir=data_dir,
            with_contender=not no_contender,
            contender_tps=tps,
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
@click.option(
    "-y", "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
def nuke(artifacts_only, data_dir, yes):
    """Delete all playground data and start fresh."""
    if not yes:
        click.confirm("Are you sure you want to delete all playground data?", abort=True)
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
    from mev_playground.config import StaticIPs
    from mev_playground.components.reth import DEFAULT_IMAGE as RETH_IMAGE
    from mev_playground.components.lighthouse import DEFAULT_IMAGE as LIGHTHOUSE_IMAGE
    from mev_playground.components.mev_boost import DEFAULT_IMAGE as MEV_BOOST_IMAGE

    console.print("[bold]MEV Playground Configuration[/bold]\n")

    console.print("[cyan]Network:[/cyan]")
    console.print(f"  Chain ID:         3151908")
    console.print(f"  Seconds per slot: 12")
    console.print(f"  Validators:       {NUM_VALIDATORS}")

    console.print("\n[cyan]Components:[/cyan]")
    console.print(f"  Execution:  {RETH_IMAGE}")
    console.print(f"  Consensus:  {LIGHTHOUSE_IMAGE}")
    console.print(f"  Relay:      turbo-relay-combined:latest")
    console.print(f"  Builder:    {get_rbuilder_image()}")
    console.print(f"  Boost:      {MEV_BOOST_IMAGE}")

    console.print(f"\n[cyan]Data Directory:[/cyan]")
    console.print(f"  {DEFAULT_DATA_DIR}")

    console.print("\n[cyan]Static IPs:[/cyan]")
    console.print(f"  Reth:         {StaticIPs.RETH}")
    console.print(f"  Lighthouse:   {StaticIPs.LIGHTHOUSE_BN}")
    console.print(f"  MEV-Boost:    {StaticIPs.MEV_BOOST}")
    console.print(f"  Relay:        {StaticIPs.RELAY}")
    console.print(f"  rbuilder:     {StaticIPs.RBUILDER}")


@main.command()
@click.option(
    "--rate",
    default=5,
    help="Transactions per slot (default: 5)",
)
@click.option(
    "--slots",
    default=None,
    type=int,
    help="Number of slots to spam (default: infinite until Ctrl+C)",
)
@click.option(
    "--rpc-url",
    default="http://localhost:8545",
    help="Reth RPC URL (default: http://localhost:8545)",
)
def spam(rate, slots, rpc_url):
    """Send test transactions to populate the mempool (simple Python spammer).

    Runs continuously until Ctrl+C unless --slots is specified.
    For more advanced spamming, use 'mev-playground contender start'.
    """
    from mev_playground.spammer import TransactionSpammer

    try:
        spammer = TransactionSpammer(rpc_url=rpc_url)
        spammer.spam(tx_per_slot=rate, duration_slots=slots)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@main.group()
def contender():
    """Manage Contender transaction spammer."""
    pass


@contender.command("start")
@click.option(
    "--tps",
    default=20,
    help="Transactions per second (default: 20)",
)
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Data directory (default: {DEFAULT_DATA_DIR})",
)
def contender_start(tps, data_dir):
    """Start Contender against a running playground."""
    try:
        playground = Playground(data_dir=data_dir)
        playground.start_contender(tps=tps)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@contender.command("stop")
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Data directory (default: {DEFAULT_DATA_DIR})",
)
def contender_stop(data_dir):
    """Stop the Contender container."""
    try:
        playground = Playground(data_dir=data_dir)
        playground.stop_contender()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@main.command("assert-blocks")
@click.option(
    "--slots",
    required=True,
    type=int,
    help="Number of consecutive slots/blocks to check",
)
@click.option(
    "--extra-data",
    default=DEFAULT_EXTRA_DATA,
    help=f"Expected extraData string (default: {DEFAULT_EXTRA_DATA})",
)
@click.option(
    "--rpc-url",
    default="http://localhost:8545",
    help="Execution client RPC URL (default: http://localhost:8545)",
)
def assert_blocks(slots, extra_data, rpc_url):
    """Assert that blocks have the expected extraData for n slots.

    Useful for integration tests to verify the builder is producing blocks.
    Exits with code 0 if all blocks match, 1 on mismatch or error.
    """
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            console.print(f"[red]Error: Cannot connect to {rpc_url}[/red]")
            sys.exit(1)

        expected_bytes = extra_data.encode("utf-8")
        matched = 0
        seen_blocks = set()

        console.print(f"Checking {slots} blocks for extraData: {extra_data}")

        while matched < slots:
            latest = w3.eth.get_block("latest")
            block_num = latest["number"]

            if block_num not in seen_blocks:
                seen_blocks.add(block_num)
                actual_extra_data = latest["extraData"]

                if actual_extra_data == expected_bytes:
                    matched += 1
                    console.print(
                        f"[green]Block {block_num}: ✓ extraData matches ({extra_data}) [{matched}/{slots}][/green]"
                    )
                else:
                    # Try to decode as UTF-8 for display
                    try:
                        actual_str = actual_extra_data.decode("utf-8")
                    except UnicodeDecodeError:
                        actual_str = actual_extra_data.hex()

                    console.print(
                        f"[red]Block {block_num}: ✗ extraData mismatch[/red]"
                    )
                    console.print(f"  Expected: {extra_data}")
                    console.print(f"  Got:      {actual_str}")
                    sys.exit(1)

            time.sleep(1)

        console.print(f"[green]All {slots} blocks matched![/green]")
        sys.exit(0)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
