"""Contender transaction spammer service."""

from mev_playground.service import Service
from mev_playground.config import StaticIPs, StaticPorts

DEFAULT_IMAGE = "flashbots/contender:latest"


def contender_service(
    tps: int = 20,
    image: str = DEFAULT_IMAGE,
) -> Service:
    """Create a Contender transaction spammer service."""
    command = [
        "spam",
        "--rpc-url", f"http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}",
        "--min-balance", "10 ether",
        "--tps", str(tps),
        "--forever",
        "transfers",
    ]

    return (
        Service("contender")
        .with_image(image)
        .with_static_ip(StaticIPs.CONTENDER)
        .with_command(*command)
        .with_user("")
    )
