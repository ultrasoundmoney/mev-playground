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
        reth_data_path: Path,
        coinbase_secret_key: str = "0x" + "01" * 32,  # Default test key
    ):
        super().__init__(data_dir)
        self.config = config
        self.reth_data_path = reth_data_path
        self.coinbase_secret_key = coinbase_secret_key
        self._config_path = data_dir / "config" / "rbuilder.toml"

    @property
    def name(self) -> str:
        return "rbuilder"

    def generate_config(self) -> str:
        """Generate rbuilder TOML configuration."""
        # Strip 0x prefix from keys if present (rbuilder expects raw hex)
        coinbase_key = self.coinbase_secret_key
        if coinbase_key.startswith("0x"):
            coinbase_key = coinbase_key[2:]
        relay_key = DEFAULT_MEV_SECRET_KEY
        if relay_key.startswith("0x"):
            relay_key = relay_key[2:]

        # Note: [[relays]] table array must come AFTER all scalar values in TOML
        config_content = f'''chain = "/genesis/genesis.json"
reth_datadir = "/reth_data"
el_node_ipc_path = "/reth_data/reth.ipc"
cl_node_url = ["http://{StaticIPs.LIGHTHOUSE_BN}:{StaticPorts.LIGHTHOUSE_HTTP}"]
enabled_relays = ["ultrasound-local"]
coinbase_secret_key = "{coinbase_key}"
relay_secret_key = "{relay_key}"
live_builders = ["mgp-ordering"]
jsonrpc_server_port = {StaticPorts.RBUILDER_RPC}
jsonrpc_server_ip = "0.0.0.0"
log_level = "info,rbuilder=debug"
log_json = false
full_telemetry_server_port = 6060
full_telemetry_server_ip = "0.0.0.0"
root_hash_use_sparse_trie = true
root_hash_compare_sparse_trie = false
extra_data = "🦇🔊"
slot_delta_to_start_bidding_ms = -12000

[[relays]]
name = "ultrasound-local"
url = "http://{StaticIPs.RELAY}:{StaticPorts.RELAY_HTTP}"
use_ssz_for_submit = false
use_gzip_for_submit = false
priority = 0
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

        # Get artifacts path for genesis.json
        artifacts_path = self.data_dir / "artifacts"

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
                # Mount Reth data directory for IPC and state access
                Mount(
                    target="/reth_data",
                    source=str(self.reth_data_path),
                    type="bind",
                ),
                # Mount artifacts for genesis.json
                Mount(
                    target="/genesis",
                    source=str(artifacts_path),
                    type="bind",
                    read_only=True,
                ),
            ],
            healthcheck={
                "test": ["NONE"],  # Distroless image has no shell; rely on container running
                "interval": 10000000000,
                "timeout": 5000000000,
                "retries": 10,
                "start_period": 60000000000,  # 60s start period for rbuilder to initialize
            },
            depends_on=["reth", "mev-ultrasound-relay", "lighthouse-bn"],
        )

    @property
    def rpc_url(self) -> str:
        return f"http://{StaticIPs.RBUILDER}:{StaticPorts.RBUILDER_RPC}"
