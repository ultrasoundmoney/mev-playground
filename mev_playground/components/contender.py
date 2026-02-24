"""Contender transaction spammer service."""

from mev_playground.service import Service
from mev_playground.config import StaticIPs, StaticPorts

DEFAULT_IMAGE = "flashbots/contender:latest"


def contender_service(
    tps: int = 20,
    name: str = "contender",
    static_ip: str = StaticIPs.CONTENDER,
    image: str = DEFAULT_IMAGE,
) -> Service:
    """Create a Contender transaction spammer service.

    Sends transfers to Reth's public mempool. Both builders pick up
    transactions from the same mempool via IPC.
    """
    command = [
        "spam",
        "--rpc-url", f"http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}",
        "--min-balance", "10 ether",
        "--tps", str(tps),
        "--forever",
        "transfers",
    ]

    return (
        Service(name)
        .with_image(image)
        .with_static_ip(static_ip)
        .with_command(*command)
        .with_user("")
    )
