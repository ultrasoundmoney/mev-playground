"""Contender transaction spammer service."""

from mev_playground.service import Service
from mev_playground.config import StaticIPs, StaticPorts

DEFAULT_IMAGE = "flashbots/contender:latest"


def contender_service(
    builder_url: str,
    private_key: str,
    scenario_dir: str,
    tps: int = 20,
    name: str = "contender",
    static_ip: str = StaticIPs.CONTENDER,
    image: str = DEFAULT_IMAGE,
) -> Service:
    """Create a Contender transaction spammer service.

    Sends bundles via eth_sendBundle to the specified builder.
    Each builder receives different private transactions, enabling
    block merging at the relay.
    """
    command = [
        "spam",
        "/scenarios/bundles.toml",
        "--rpc-url", f"http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}",
        "--builder-url", builder_url,
        "-p", private_key,
        "--min-balance", "10 ether",
        "--tps", str(tps),
        "--forever",
    ]

    return (
        Service(name)
        .with_image(image)
        .with_static_ip(static_ip)
        .with_command(*command)
        .with_mount("/scenarios", scenario_dir, read_only=True)
        .with_user("")
    )
