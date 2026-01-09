"""Main orchestrator for MEV Playground."""

import shutil
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from mev_playground.config import PlaygroundConfig, DEFAULT_DATA_DIR
from mev_playground.docker.controller import DockerController
from mev_playground.docker.network import NetworkManager
from mev_playground.artifacts import (
    generate_jwt_secret,
    generate_el_genesis,
    generate_beacon_genesis,
)
from mev_playground.artifacts.keys import get_validator_keys, write_validator_files
from mev_playground.components.reth import RethComponent
from mev_playground.components.lighthouse import (
    LighthouseBeaconComponent,
    LighthouseValidatorComponent,
)
from mev_playground.components.mev_boost import MEVBoostComponent
from mev_playground.components.redis import RedisComponent
from mev_playground.components.postgres import create_relay_databases
from mev_playground.components.relay import UltrasoundRelayComponent
from mev_playground.components.rbuilder import RbuilderComponent
from mev_playground.components.dora import DoraComponent


console = Console()


class Playground:
    """Main orchestrator for the MEV playground."""

    def __init__(
        self,
        config: Optional[PlaygroundConfig] = None,
        data_dir: Optional[Path] = None,
        relay_image: Optional[str] = None,
        builder: str = "rbuilder",
        builder_image: Optional[str] = None,
    ):
        """Initialize the playground.

        Args:
            config: Playground configuration
            data_dir: Override data directory
            relay_image: Override relay image
            builder: Builder type ("rbuilder", "custom", or "none")
            builder_image: Custom builder image (if builder="custom")
        """
        self.config = config or PlaygroundConfig()

        if data_dir:
            self.config.data_dir = data_dir

        if relay_image:
            self.config.mev.relay.image = relay_image

        if builder == "none":
            self.config.mev.builder.enabled = False
        elif builder == "custom" and builder_image:
            self.config.mev.builder.type = "custom"
            self.config.mev.builder.image = builder_image
        elif builder == "rbuilder":
            self.config.mev.builder.type = "rbuilder"

        self.controller = DockerController()
        self.network_manager = NetworkManager(self.controller.client)

        # Component instances (initialized during start)
        self._components = {}

    def _ensure_artifacts(self) -> None:
        """Ensure all artifacts are generated."""
        artifacts_dir = self.config.artifacts_dir

        # Check if artifacts already exist
        jwt_path = artifacts_dir / "jwt.hex"
        genesis_path = artifacts_dir / "genesis.json"
        validators_dir = artifacts_dir / "validators"
        beacon_dir = artifacts_dir / "beacon"

        if all([
            jwt_path.exists(),
            genesis_path.exists(),
            validators_dir.exists(),
            beacon_dir.exists(),
        ]):
            console.print("[green]Using existing artifacts[/green]")
            return

        console.print("[yellow]Generating artifacts...[/yellow]")

        # Ensure artifacts directory exists
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Generate JWT secret
        generate_jwt_secret(jwt_path)
        console.print("  JWT secret generated")

        # Copy EL genesis from fixture
        generate_el_genesis(genesis_path, 0)
        console.print("  EL genesis copied")

        # Get pre-generated validator keys and write to disk
        keys = get_validator_keys(self.config.validators.count)
        write_validator_files(validators_dir, keys)
        console.print(f"  {len(keys)} validator keys loaded")

        # Copy beacon chain genesis from fixtures
        generate_beacon_genesis(beacon_dir)

        # Copy JWT to beacon dir for Lighthouse
        shutil.copy(jwt_path, beacon_dir / "jwt.hex")

    def _collect_images(self) -> list[str]:
        """Collect all Docker images that need to be pulled."""
        images = [
            self.config.execution.image,
            self.config.consensus.image,
            self.config.mev.boost.image,
            "pk910/dora-the-explorer:latest",
        ]
        # Relay/builder components disabled for now
        # images.extend([
        #     self.config.mev.relay.image,
        #     "redis:7-alpine",
        #     "postgres:15-alpine",
        # ])
        # if self.config.mev.builder.enabled:
        #     images.append(self.config.mev.builder.image)
        return images

    def _create_components(self) -> None:
        """Create all component instances."""
        data_dir = self.config.data_dir

        # Core Ethereum stack
        self._components["reth"] = RethComponent(data_dir, self.config)
        self._components["lighthouse-bn"] = LighthouseBeaconComponent(
            data_dir, self.config, enable_mev_boost=True
        )
        self._components["lighthouse-vc"] = LighthouseValidatorComponent(
            data_dir, self.config
        )
        self._components["mev-boost"] = MEVBoostComponent(data_dir, self.config)

        # Block explorer
        self._components["dora"] = DoraComponent(data_dir)

        # Relay infrastructure - disabled for now
        # self._components["redis"] = RedisComponent(data_dir)
        # mevdb, localdb, globaldb = create_relay_databases(data_dir)
        # self._components["mevdb"] = mevdb
        # self._components["localdb"] = localdb
        # self._components["globaldb"] = globaldb

        # Relay - disabled for now
        # self._components["mev-ultrasound-relay"] = UltrasoundRelayComponent(
        #     data_dir,
        #     self.config,
        #     self._genesis_timestamp,
        #     self._genesis_validators_root,
        # )

        # Builder - disabled for now
        # if self.config.mev.builder.enabled and self.config.mev.builder.type == "rbuilder":
        #     self._components["rbuilder"] = RbuilderComponent(data_dir, self.config)

    def start(self) -> None:
        """Start all playground components."""
        console.print("[bold blue]Starting MEV Playground[/bold blue]")

        # Ensure artifacts exist
        self._ensure_artifacts()

        # Create network
        console.print("Creating Docker network...")
        self.network_manager.create_network()

        # Pull images
        console.print("Pulling Docker images...")
        images = self._collect_images()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Pulling images...", total=len(images))
            self.controller.pull_images_parallel(images)
            progress.update(task, completed=len(images))

        # Create components
        self._create_components()

        # Start components in order
        startup_order = [
            # Core Ethereum
            "reth",
            "lighthouse-bn",
            "mev-boost",
            "lighthouse-vc",
            # Tools
            "dora",
            # Relay infrastructure - disabled for now
            # "redis",
            # "mevdb",
            # "localdb",
            # "globaldb",
            # "mev-ultrasound-relay",
            # "rbuilder",
        ]

        # Clean up any existing containers from previous runs
        console.print("Cleaning up existing containers...")
        self.controller.cleanup_existing(startup_order)

        console.print("Starting containers...")
        for name in startup_order:
            if name in self._components:
                console.print(f"  Starting {name}...")
                self._components[name].start(self.controller)

        # Wait for health checks
        console.print("Waiting for services to become healthy...")
        self.controller.wait_for_all_healthy(timeout=180)

        console.print("[bold green]MEV Playground is running![/bold green]")
        self._print_endpoints()

    def stop(self) -> None:
        """Stop all playground components (keep data)."""
        console.print("[yellow]Stopping MEV Playground...[/yellow]")
        self.controller.stop_all()
        console.print("[green]Stopped. Data preserved.[/green]")

    def nuke(self, artifacts_only: bool = False) -> None:
        """Remove all playground data.

        Args:
            artifacts_only: If True, only remove artifacts (keep chain data)
        """
        console.print("[red]Nuking MEV Playground...[/red]")

        # Stop and remove containers
        self.controller.stop_all()
        self.controller.remove_all(force=True)

        # Remove network
        self.network_manager.remove_network()

        # Remove data
        if artifacts_only:
            artifacts_dir = self.config.artifacts_dir
            if artifacts_dir.exists():
                shutil.rmtree(artifacts_dir)
            console.print("[green]Artifacts removed. Chain data preserved.[/green]")
        else:
            data_dir = self.config.data_dir
            if data_dir.exists():
                shutil.rmtree(data_dir)
            console.print("[green]All data removed.[/green]")

    def status(self) -> dict:
        """Get status of all components."""
        status = {}
        for name in self.controller.list_containers():
            container = self.controller.get_container(name)
            if container:
                container.reload()
                health = container.attrs.get("State", {}).get("Health", {})
                status[name] = {
                    "status": container.status,
                    "health": health.get("Status", "none"),
                }
        return status

    def logs(self, component: str, tail: int = 100) -> str:
        """Get logs from a component."""
        return self.controller.get_container_logs(component, tail)

    def _print_endpoints(self) -> None:
        """Print all available endpoints."""
        console.print("\n[bold]Endpoints:[/bold]")
        console.print(f"  Reth HTTP:        http://localhost:{8545}")
        console.print(f"  Reth WS:          ws://localhost:{8546}")
        console.print(f"  Lighthouse:       http://localhost:{3500}")
        console.print(f"  MEV-Boost:        http://localhost:{18550}")
        console.print(f"  Dora Explorer:    http://localhost:{8080}")
        # Relay/builder disabled for now
        # console.print(f"  Relay:            http://localhost:{80}")
        # if "rbuilder" in self._components:
        #     console.print(f"  rbuilder RPC:     http://localhost:{8645}")
        console.print("")
