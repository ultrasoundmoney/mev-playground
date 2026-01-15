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
    generate_genesis,
    GenesisGeneratorConfig,
    get_genesis_validators_root_from_dir,
    get_genesis_time_from_dir,
)
from mev_playground.artifacts.keys import generate_validator_keystores
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
from mev_playground.components.contender import ContenderComponent


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
        with_contender: bool = False,
        contender_tps: int = 20,
    ):
        """Initialize the playground.

        Args:
            config: Playground configuration
            data_dir: Override data directory
            relay_image: Override relay image
            builder: Builder type ("rbuilder", "custom", or "none")
            builder_image: Custom builder image (if builder="custom")
            with_contender: Start Contender tx spammer with the playground
            contender_tps: Contender transactions per second
        """
        self.config = config or PlaygroundConfig()
        self.with_contender = with_contender
        self.contender_tps = contender_tps

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
        """Ensure all artifacts are generated using ethereum-genesis-generator."""
        artifacts_dir = self.config.artifacts_dir

        # Check if artifacts already exist (all required files)
        jwt_path = artifacts_dir / "jwt.hex"
        genesis_path = artifacts_dir / "genesis.json"
        beacon_dir = artifacts_dir / "beacon"
        validators_dir = artifacts_dir / "validators"
        genesis_ssz_path = beacon_dir / "genesis.ssz"
        config_yaml_path = beacon_dir / "config.yaml"
        validators_root_path = beacon_dir / "genesis_validators_root.txt"
        validator_definitions_path = validators_dir / "validator_definitions.yml"

        if all([
            jwt_path.exists(),
            genesis_path.exists(),
            genesis_ssz_path.exists(),
            config_yaml_path.exists(),
            validators_root_path.exists(),
            validator_definitions_path.exists(),
        ]):
            console.print("[green]Using existing artifacts[/green]")
            return

        console.print("[yellow]Generating artifacts using ethereum-genesis-generator...[/yellow]")

        # Ensure artifacts directory exists
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        beacon_dir.mkdir(parents=True, exist_ok=True)

        # Generate JWT secret
        generate_jwt_secret(jwt_path)
        console.print("  JWT secret generated")

        # Create genesis generator config from playground config
        genesis_config = GenesisGeneratorConfig(
            chain_id=self.config.network.chain_id,
            preset=self.config.network.preset,
            genesis_delay=self.config.network.genesis_delay,
            seconds_per_slot=self.config.network.seconds_per_slot,
            slot_duration_ms=self.config.network.seconds_per_slot * 1000,
            num_validators=self.config.validators.count,
            mnemonic=self.config.network.mnemonic,
            electra_fork_epoch=self.config.network.electra_fork_epoch,
            fulu_fork_epoch=self.config.network.fulu_fork_epoch,
            genesis_generator_image=self.config.network.genesis_generator_image,
        )

        # Generate EL and CL genesis using Docker
        console.print("  Running ethereum-genesis-generator (this may take a moment)...")
        genesis_data = generate_genesis(
            output_dir=beacon_dir,
            config=genesis_config,
            verbose=False,
        )

        # Copy EL genesis to main artifacts dir (for components that expect it there)
        shutil.copy(genesis_data.el_genesis_path, genesis_path)

        console.print(f"  Genesis generated with {self.config.validators.count} validators")
        console.print(f"  Genesis time: {genesis_data.genesis_time}")

        # Generate validator keystores using eth2-val-tools (same mnemonic as genesis)
        console.print("  Generating validator keystores...")
        generate_validator_keystores(
            output_dir=validators_dir,
            mnemonic=self.config.network.mnemonic,
            count=self.config.validators.count,
            verbose=False,
        )
        console.print(f"  {self.config.validators.count} validator keystores generated")
        console.print(f"  Genesis validators root: {genesis_data.genesis_validators_root}")

        # Copy JWT to beacon dir for Lighthouse
        shutil.copy(jwt_path, beacon_dir / "jwt.hex")

    def _collect_images(self) -> list[str]:
        """Collect all Docker images that need to be pulled."""
        images = [
            self.config.execution.image,
            self.config.consensus.image,
            self.config.mev.boost.image,
            "pk910/dora-the-explorer:latest",
            self.config.mev.relay.image,
            "redis:7-alpine",
            "postgres:15-alpine",
        ]
        if self.config.mev.builder.enabled:
            images.append(self.config.mev.builder.image)
        if self.with_contender:
            images.append(self.config.contender.image)
        return images

    def _create_components(self) -> None:
        """Create all component instances."""
        data_dir = self.config.data_dir
        beacon_dir = self.config.artifacts_dir / "beacon"

        # Read genesis data from generated artifacts
        genesis_time = get_genesis_time_from_dir(beacon_dir)
        genesis_validators_root = get_genesis_validators_root_from_dir(beacon_dir)

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

        # Relay infrastructure
        self._components["redis"] = RedisComponent(data_dir)
        mevdb, localdb, globaldb = create_relay_databases(data_dir)
        self._components["mevdb"] = mevdb
        self._components["localdb"] = localdb
        self._components["globaldb"] = globaldb

        # Relay
        self._components["mev-ultrasound-relay"] = UltrasoundRelayComponent(
            data_dir,
            self.config,
            genesis_time,
            genesis_validators_root,
        )

        # Builder
        if self.config.mev.builder.enabled and self.config.mev.builder.type == "rbuilder":
            reth_component = self._components["reth"]
            self._components["rbuilder"] = RbuilderComponent(
                data_dir,
                self.config,
                reth_data_path=reth_component.data_path,
            )

        # Contender tx spammer
        if self.with_contender:
            self._components["contender"] = ContenderComponent(
                data_dir,
                tps=self.contender_tps,
                image=self.config.contender.image,
                extra_args=self.config.contender.extra_args,
            )

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
            # Relay infrastructure
            "redis",
            "mevdb",
            "localdb",
            "globaldb",
            "mev-ultrasound-relay",
        ]
        if self.config.mev.builder.enabled:
            startup_order.append("rbuilder")

        # Clean up any existing containers from previous runs
        all_containers = startup_order + (["contender"] if self.with_contender else [])
        console.print("Cleaning up existing containers...")
        self.controller.cleanup_existing(all_containers)

        console.print("Starting containers...")
        for name in startup_order:
            if name in self._components:
                # Add delay before relay to ensure genesis time has passed
                if name == "mev-ultrasound-relay":
                    import time
                    console.print("  Waiting for genesis time to pass...")
                    time.sleep(10)
                console.print(f"  Starting {name}...")
                self._components[name].start(self.controller)

        # Wait for health checks (before starting Contender which has no healthcheck)
        console.print("Waiting for services to become healthy...")
        self.controller.wait_for_all_healthy(timeout=180)

        # Start Contender after other services are healthy (it has no healthcheck)
        if self.with_contender and "contender" in self._components:
            console.print("  Starting contender...")
            self._components["contender"].start(self.controller)

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
        console.print(f"  Relay:            http://localhost:{80}")
        if "rbuilder" in self._components:
            console.print(f"  rbuilder RPC:     http://localhost:{8645}")
        console.print("")

    def start_contender(self, tps: int = 20) -> None:
        """Start Contender against a running playground.

        Args:
            tps: Transactions per second
        """
        # Check if playground is running by looking for reth container in Docker
        try:
            reth = self.controller.client.containers.get("reth")
            if reth.status != "running":
                raise RuntimeError("Playground is not running. Start it first with 'mev-playground start'")
        except Exception:
            raise RuntimeError("Playground is not running. Start it first with 'mev-playground start'")

        # Pull image if needed
        console.print(f"Pulling {self.config.contender.image}...")
        self.controller.pull_image(self.config.contender.image)

        # Create and start contender
        contender = ContenderComponent(
            self.config.data_dir,
            tps=tps,
            image=self.config.contender.image,
            extra_args=self.config.contender.extra_args,
        )

        # Remove existing contender container if any
        self.controller.remove_container("contender", force=True)

        console.print(f"Starting Contender with {tps} TPS...")
        contender.start(self.controller)
        console.print("[green]Contender is running![/green]")

    def stop_contender(self) -> None:
        """Stop the Contender container."""
        container = self.controller.get_container("contender")
        if container:
            console.print("Stopping Contender...")
            self.controller.stop_container("contender")
            self.controller.remove_container("contender", force=True)
            console.print("[green]Contender stopped.[/green]")
        else:
            console.print("[yellow]Contender is not running.[/yellow]")
