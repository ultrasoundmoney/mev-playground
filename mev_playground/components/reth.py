"""Reth execution client service."""

from pathlib import Path

from mev_playground.service import Service
from mev_playground.config import StaticIPs, StaticPorts

DEFAULT_IMAGE = "ghcr.io/paradigmxyz/reth:v1.8.2"


def reth_service(data_dir: Path) -> Service:
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

    return (
        Service("reth")
        .with_image(DEFAULT_IMAGE)
        .with_static_ip(StaticIPs.RETH)
        .with_command(*command)
        .with_port(StaticPorts.RETH_HTTP, StaticPorts.RETH_HTTP)
        .with_port(StaticPorts.RETH_WS, StaticPorts.RETH_WS)
        .with_port(StaticPorts.RETH_AUTH, StaticPorts.RETH_AUTH)
        .with_mount("/data", str(data_path))
        .with_mount("/genesis", str(artifacts_path), read_only=True)
        .with_healthcheck(
            test=[
                "CMD-SHELL",
                f"bash -c 'echo >/dev/tcp/localhost/{StaticPorts.RETH_HTTP}' 2>/dev/null || exit 1",
            ],
            interval=5000000000,
            timeout=3000000000,
            retries=10,
            start_period=10000000000,
        )
    )
