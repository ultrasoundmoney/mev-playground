"""Reth execution client component."""

from pathlib import Path
from docker.types import Mount

from mev_playground.components.base import Component, ContainerConfig
from mev_playground.config import StaticIPs, StaticPorts, PlaygroundConfig


class RethComponent(Component):
    """Reth execution client."""

    def __init__(self, data_dir: Path, config: PlaygroundConfig):
        super().__init__(data_dir)
        self.config = config
        self._data_path = data_dir / "data" / "reth"
        self._artifacts_path = data_dir / "artifacts"

    @property
    def name(self) -> str:
        return "reth"

    def get_container_config(self) -> ContainerConfig:
        # Ensure data directories exist
        self._data_path.mkdir(parents=True, exist_ok=True)

        jwt_path = self._artifacts_path / "jwt.hex"
        genesis_path = self._artifacts_path / "genesis.json"

        command = [
            "node",
            "--chain", "/genesis/genesis.json",
            "--datadir", "/data",
            "--http",
            "--http.addr", "0.0.0.0",
            "--http.port", str(StaticPorts.RETH_HTTP),
            "--http.api", "eth,net,web3,debug,trace,txpool,admin",
            "--http.corsdomain", "*",
            "--ws",
            "--ws.addr", "0.0.0.0",
            "--ws.port", str(StaticPorts.RETH_WS),
            "--ws.api", "eth,net,web3,debug,trace,txpool",
            "--authrpc.addr", "0.0.0.0",
            "--authrpc.port", str(StaticPorts.RETH_AUTH),
            "--authrpc.jwtsecret", "/genesis/jwt.hex",
            "--metrics", f"0.0.0.0:{StaticPorts.RETH_METRICS}",
            "--log.stdout.format", "terminal",
            "--full",
            "--ipcdisable",  # Disable IPC for now (can enable for rbuilder)
            # Required for proper engine API payload building
            "--engine.persistence-threshold", "0",
            "--engine.memory-block-buffer-target", "0",
        ]

        return ContainerConfig(
            name=self.name,
            image=self.config.execution.image,
            static_ip=StaticIPs.RETH,
            command=command,
            ports={
                StaticPorts.RETH_HTTP: StaticPorts.RETH_HTTP,
                StaticPorts.RETH_WS: StaticPorts.RETH_WS,
                StaticPorts.RETH_AUTH: StaticPorts.RETH_AUTH,
            },
            mounts=[
                Mount(
                    target="/data",
                    source=str(self._data_path),
                    type="bind",
                ),
                Mount(
                    target="/genesis",
                    source=str(self._artifacts_path),
                    type="bind",
                    read_only=True,
                ),
            ],
            healthcheck={
                "test": [
                    "CMD-SHELL",
                    # Use bash explicitly for /dev/tcp support
                    f"bash -c 'echo >/dev/tcp/localhost/{StaticPorts.RETH_HTTP}' 2>/dev/null || exit 1",
                ],
                "interval": 5000000000,  # 5s in nanoseconds
                "timeout": 3000000000,  # 3s
                "retries": 10,
                "start_period": 10000000000,  # 10s
            },
        )

    @property
    def http_url(self) -> str:
        return f"http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}"

    @property
    def ws_url(self) -> str:
        return f"ws://{StaticIPs.RETH}:{StaticPorts.RETH_WS}"

    @property
    def auth_url(self) -> str:
        return f"http://{StaticIPs.RETH}:{StaticPorts.RETH_AUTH}"
