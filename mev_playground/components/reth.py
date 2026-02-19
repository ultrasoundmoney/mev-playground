"""Reth execution client service."""

from pathlib import Path
from docker.types import Mount

from mev_playground.components.base import Service
from mev_playground.config import StaticIPs, StaticPorts, PlaygroundConfig


def reth_service(data_dir: Path, config: PlaygroundConfig) -> Service:
    """Create a Reth execution client service."""
    data_path = data_dir / "data" / "reth"
    artifacts_path = data_dir / "artifacts"
    data_path.mkdir(parents=True, exist_ok=True)

    command = [
        "node",
        "--chain", "/genesis/genesis.json",
        "--datadir", "/data",
        "--http",
        "--http.addr", "0.0.0.0",
        "--http.port", str(StaticPorts.RETH_HTTP),
        "--http.api", "all",
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
        "--log.file.directory", "/data/logs",
        "--full",
        "--ipcpath", "/data/reth.ipc",
        "--engine.persistence-threshold", "0",
        "--engine.memory-block-buffer-target", "0",
        "--db.exclusive", "false",
    ]

    return Service(
        name="reth",
        image=config.execution.image,
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
                source=str(data_path),
                type="bind",
            ),
            Mount(
                target="/genesis",
                source=str(artifacts_path),
                type="bind",
                read_only=True,
            ),
        ],
        healthcheck={
            "test": [
                "CMD-SHELL",
                f"bash -c 'echo >/dev/tcp/localhost/{StaticPorts.RETH_HTTP}' 2>/dev/null || exit 1",
            ],
            "interval": 5000000000,  # 5s in nanoseconds
            "timeout": 3000000000,  # 3s
            "retries": 10,
            "start_period": 10000000000,  # 10s
        },
    )
