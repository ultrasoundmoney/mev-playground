"""Reth execution client service."""

import json
from pathlib import Path

from mev_playground.service import Service
from mev_playground.config import (
    StaticIPs,
    StaticPorts,
    DEFAULT_BUILDER_COLLATERAL_MAP,
    RELAY_FEE_RECIPIENT,
    DISPERSE_CONTRACT_ADDRESS,
)

DEFAULT_IMAGE = "reth-simulator:latest"


def reth_service(data_dir: Path, image: str = DEFAULT_IMAGE) -> Service:
    """Create a Reth execution client service.

    When using reth-simulator (default), block merging CLI flags are added
    automatically along with the required collateral map config file.
    """
    data_path = data_dir / "data" / "reth"
    artifacts_path = data_dir / "artifacts"
    config_path = data_dir / "config" / "reth"
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
        # Block merging extension flags (reth-simulator)
        "--enable-ext",
        "--builder-collateral-map-path", "/config/builder-collateral-map.json",
        "--relay-fee-recipient", RELAY_FEE_RECIPIENT,
        "--disperse-address", DISPERSE_CONTRACT_ADDRESS,
    ]

    # Write builder collateral map config
    config_path.mkdir(parents=True, exist_ok=True)
    collateral_map_file = config_path / "builder-collateral-map.json"
    collateral_map_file.write_text(json.dumps(DEFAULT_BUILDER_COLLATERAL_MAP, indent=2))

    return (
        Service("reth")
        .with_image(image)
        .with_static_ip(StaticIPs.RETH)
        .with_command(*command)
        .with_port(StaticPorts.RETH_HTTP, StaticPorts.RETH_HTTP)
        .with_port(StaticPorts.RETH_WS, StaticPorts.RETH_WS)
        .with_port(StaticPorts.RETH_AUTH, StaticPorts.RETH_AUTH)
        .with_mount("/data", str(data_path))
        .with_mount("/genesis", str(artifacts_path), read_only=True)
        .with_mount("/config", str(config_path.resolve()), read_only=True)
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
