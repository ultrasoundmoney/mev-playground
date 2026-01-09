"""rbuilder component."""

from pathlib import Path
from docker.types import Mount

from mev_playground.components.base import Component, ContainerConfig
from mev_playground.config import (
    StaticIPs,
    StaticPorts,
    PlaygroundConfig,
    DEFAULT_MEV_SECRET_KEY,
)


class RbuilderComponent(Component):
    """rbuilder block builder."""

    def __init__(
        self,
        data_dir: Path,
        config: PlaygroundConfig,
        coinbase_secret_key: str = "0x" + "01" * 32,  # Default test key
    ):
        super().__init__(data_dir)
        self.config = config
        self.coinbase_secret_key = coinbase_secret_key
        self._config_path = data_dir / "config" / "rbuilder.toml"

    @property
    def name(self) -> str:
        return "rbuilder"

    def generate_config(self) -> str:
        """Generate rbuilder TOML configuration."""
        config_content = f'''# rbuilder configuration for mev-playground

# Chain configuration
chain = "holesky"

# Consensus layer connection
cl_node_url = ["http://{StaticIPs.LIGHTHOUSE_BN}:{StaticPorts.LIGHTHOUSE_HTTP}"]

# Relay configuration
enabled_relays = ["ultrasound-local"]

[[relays]]
name = "ultrasound-local"
url = "http://{StaticIPs.RELAY}:{StaticPorts.RELAY_HTTP}"
mode = "full"
use_ssz_for_submit = false
use_gzip_for_submit = false
priority = 0

# Builder configuration
coinbase_secret_key = "{self.coinbase_secret_key}"
relay_secret_key = "{DEFAULT_MEV_SECRET_KEY}"

# Builders to run
live_builders = ["mgp-ordering"]

# JSON-RPC server for bundle submissions
jsonrpc_server_port = {StaticPorts.RBUILDER_RPC}
jsonrpc_server_ip = "0.0.0.0"

# Logging
log_level = "info,rbuilder=debug"
log_json = false

# Telemetry
full_telemetry_server_port = 6060
full_telemetry_server_ip = "0.0.0.0"

# Note: reth_datadir and el_node_ipc_path need to be set based on
# how rbuilder accesses reth (shared volume or IPC)
'''
        return config_content

    def write_config(self) -> Path:
        """Write the rbuilder configuration file."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(self.generate_config())
        return self._config_path

    def get_container_config(self) -> ContainerConfig:
        # Ensure config is written
        self.write_config()

        command = [
            "run",
            "/config/rbuilder.toml",
        ]

        # Add any extra environment variables
        environment = dict(self.config.mev.builder.extra_env)
        environment["COINBASE_SECRET_KEY"] = self.coinbase_secret_key
        environment["RELAY_SECRET_KEY"] = DEFAULT_MEV_SECRET_KEY

        return ContainerConfig(
            name=self.name,
            image=self.config.mev.builder.image,
            static_ip=StaticIPs.RBUILDER,
            command=command,
            environment=environment,
            ports={
                StaticPorts.RBUILDER_RPC: StaticPorts.RBUILDER_RPC,
                6060: 6060,  # Telemetry
            },
            mounts=[
                Mount(
                    target="/config",
                    source=str(self._config_path.parent),
                    type="bind",
                    read_only=True,
                ),
            ],
            healthcheck={
                "test": [
                    "CMD-SHELL",
                    # Use bash explicitly for /dev/tcp support
                    f"bash -c 'echo >/dev/tcp/localhost/{StaticPorts.RBUILDER_RPC}' 2>/dev/null || exit 1",
                ],
                "interval": 10000000000,
                "timeout": 5000000000,
                "retries": 10,
                "start_period": 30000000000,
            },
            depends_on=["mev-ultrasound-relay", "lighthouse-bn"],
        )

    @property
    def rpc_url(self) -> str:
        return f"http://{StaticIPs.RBUILDER}:{StaticPorts.RBUILDER_RPC}"
