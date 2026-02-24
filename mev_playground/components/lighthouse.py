"""Lighthouse consensus client services."""

from pathlib import Path

from mev_playground.service import Service
from mev_playground.config import StaticIPs, StaticPorts, PROPOSER_FEE_RECIPIENT

DEFAULT_IMAGE = "sigp/lighthouse:v8.0.0-rc.2"


def lighthouse_beacon_service(
    data_dir: Path,
    enable_mev_boost: bool = True,
) -> Service:
    """Create a Lighthouse beacon node service."""
    data_path = data_dir / "data" / "lighthouse" / "beacon"
    artifacts_path = data_dir / "artifacts"
    data_path.mkdir(parents=True, exist_ok=True)

    command = [
        "lighthouse",
        "beacon_node",
        "--datadir", "/data",
        "--testnet-dir", "/config",
        "--execution-endpoint", f"http://{StaticIPs.RETH}:{StaticPorts.RETH_AUTH}",
        "--execution-jwt", "/config/jwt.hex",
        "--http",
        "--http-address", "0.0.0.0",
        "--http-port", str(StaticPorts.LIGHTHOUSE_HTTP),
        "--http-allow-origin", "*",
        "--metrics",
        "--metrics-address", "0.0.0.0",
        "--metrics-port", str(StaticPorts.LIGHTHOUSE_METRICS),
        "--staking",
        "--disable-peer-scoring",
        "--disable-packet-filter",
        "--enable-private-discovery",
        "--target-peers", "0",
        "--disable-upnp",
        "--disable-enr-auto-update",
        "--enr-address", StaticIPs.LIGHTHOUSE_BN,
        "--enr-udp-port", str(StaticPorts.LIGHTHOUSE_P2P),
        "--enr-tcp-port", str(StaticPorts.LIGHTHOUSE_P2P),
        "--port", str(StaticPorts.LIGHTHOUSE_P2P),
        "--always-prepare-payload",
        "--prepare-payload-lookahead", "8000",
        "--suggested-fee-recipient", PROPOSER_FEE_RECIPIENT,
    ]

    if enable_mev_boost:
        command.extend([
            "--builder", f"http://{StaticIPs.MEV_BOOST}:{StaticPorts.MEV_BOOST}",
            "--builder-fallback-epochs-since-finalization", "0",
            "--builder-fallback-disable-checks",
            "--builder-header-timeout", "3000",  # 3s max allowed by lighthouse
        ])

    return (
        Service("lighthouse-bn")
        .with_image(DEFAULT_IMAGE)
        .with_static_ip(StaticIPs.LIGHTHOUSE_BN)
        .with_command(*command)
        .with_port(StaticPorts.LIGHTHOUSE_HTTP, StaticPorts.LIGHTHOUSE_HTTP)
        .with_port(StaticPorts.LIGHTHOUSE_METRICS, StaticPorts.LIGHTHOUSE_METRICS)
        .with_mount("/data", str(data_path))
        .with_mount("/config", str(artifacts_path / "beacon"), read_only=True)
        .with_healthcheck(
            test=[
                "CMD-SHELL",
                f"bash -c 'echo >/dev/tcp/localhost/{StaticPorts.LIGHTHOUSE_HTTP}' 2>/dev/null || exit 1",
            ],
            interval=5000000000,
            timeout=3000000000,
            retries=20,
            start_period=30000000000,
        )
        .with_depends_on("reth")
    )


def lighthouse_validator_service(data_dir: Path) -> Service:
    """Create a Lighthouse validator client service."""
    data_path = data_dir / "data" / "lighthouse" / "validator"
    artifacts_path = data_dir / "artifacts"
    data_path.mkdir(parents=True, exist_ok=True)

    command = [
        "lighthouse",
        "validator_client",
        "--datadir", "/data",
        "--testnet-dir", "/config",
        "--beacon-nodes", f"http://{StaticIPs.LIGHTHOUSE_BN}:{StaticPorts.LIGHTHOUSE_HTTP}",
        "--init-slashing-protection",
        "--http",
        "--http-address", "0.0.0.0",
        "--http-port", "5062",
        "--http-allow-origin", "*",
        "--unencrypted-http-transport",
        "--graffiti", "mev-playground",
        "--suggested-fee-recipient", PROPOSER_FEE_RECIPIENT,
        "--builder-proposals",
        "--prefer-builder-proposals",
    ]

    return (
        Service("lighthouse-vc")
        .with_image(DEFAULT_IMAGE)
        .with_static_ip(StaticIPs.LIGHTHOUSE_VC)
        .with_command(*command)
        .with_mount("/config", str(artifacts_path / "beacon"), read_only=True)
        .with_mount("/data/validators", str(artifacts_path / "validators"))
        .with_healthcheck(
            test=[
                "CMD-SHELL",
                "bash -c 'echo >/dev/tcp/localhost/5062' 2>/dev/null || exit 1",
            ],
            interval=5000000000,
            timeout=3000000000,
            retries=10,
            start_period=10000000000,
        )
        .with_depends_on("lighthouse-bn")
    )
