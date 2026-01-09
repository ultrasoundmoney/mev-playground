"""Dora the Explorer block explorer component."""

from pathlib import Path
from docker.types import Mount

from mev_playground.components.base import Component, ContainerConfig
from mev_playground.config import StaticIPs, StaticPorts


# Dora default HTTP port
DORA_PORT = 8080


class DoraComponent(Component):
    """Dora the Explorer - lightweight beaconchain explorer."""

    def __init__(self, data_dir: Path):
        super().__init__(data_dir)
        self._config_path = data_dir / "config" / "dora"

    @property
    def name(self) -> str:
        return "dora"

    def _generate_config(self) -> str:
        """Generate Dora configuration YAML."""
        return f"""logging:
  outputLevel: "info"

chain:
  displayName: "MEV Playground Devnet"

server:
  host: "0.0.0.0"
  port: "{DORA_PORT}"

frontend:
  enabled: true
  siteName: "MEV Playground Explorer"
  siteSubtitle: "Local Devnet"
  ethExplorerLink: ""

beaconapi:
  endpoints:
    - name: "lighthouse"
      url: "http://{StaticIPs.LIGHTHOUSE_BN}:{StaticPorts.LIGHTHOUSE_HTTP}"
  localCacheSize: 100

executionapi:
  endpoints:
    - name: "reth"
      url: "http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}"
  depositDeployBlock: 0

indexer:
  inMemoryEpochs: 3
  activityHistoryLength: 6
  disableSynchronizer: false
  syncEpochCooldown: 1
  maxParallelValidatorSetRequests: 1

database:
  engine: "sqlite"
  sqlite:
    file: "/data/dora.sqlite"
"""

    def get_container_config(self) -> ContainerConfig:
        # Ensure config directory exists and write config
        self._config_path.mkdir(parents=True, exist_ok=True)
        config_file = self._config_path / "config.yaml"
        config_file.write_text(self._generate_config())

        # Data directory for sqlite
        data_path = self.data_dir / "data" / "dora"
        data_path.mkdir(parents=True, exist_ok=True)

        return ContainerConfig(
            name=self.name,
            image="pk910/dora-the-explorer:latest",
            static_ip=StaticIPs.DORA,
            command=[
                "-config", "/config/config.yaml",
            ],
            ports={
                DORA_PORT: DORA_PORT,
            },
            mounts=[
                Mount(
                    target="/config",
                    source=str(self._config_path),
                    type="bind",
                    read_only=True,
                ),
                Mount(
                    target="/data",
                    source=str(data_path),
                    type="bind",
                ),
            ],
            healthcheck={
                "test": [
                    "CMD-SHELL",
                    f"bash -c 'echo >/dev/tcp/localhost/{DORA_PORT}' 2>/dev/null || exit 1",
                ],
                "interval": 5000000000,  # 5 seconds
                "timeout": 3000000000,   # 3 seconds
                "retries": 10,
                "start_period": 10000000000,  # 10 seconds
            },
            depends_on=["lighthouse-bn", "reth"],
        )

    @property
    def url(self) -> str:
        return f"http://localhost:{DORA_PORT}"
