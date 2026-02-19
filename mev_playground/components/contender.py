"""Contender transaction spammer service."""

from mev_playground.components.base import Service
from mev_playground.config import StaticIPs, StaticPorts


def contender_service(
    tps: int = 20,
    extra_args: list[str] | None = None,
    image: str = "flashbots/contender:latest",
) -> Service:
    """Create a Contender transaction spammer service."""
    command = [
        "spam",
        "--rpc-url", f"http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}",
        "--min-balance", "10 ether",
        "--tps", str(tps),
        "--forever",
    ]
    command.extend(extra_args or [])
    command.append("transfers")

    return Service(
        name="contender",
        image=image,
        static_ip=StaticIPs.CONTENDER,
        command=command,
        user="",  # Use image default user (don't override with host user)
    )
