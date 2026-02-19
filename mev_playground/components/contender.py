"""Contender transaction spammer service."""

from mev_playground.service import Service
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

    return (
        Service("contender")
        .with_image(image)
        .with_static_ip(StaticIPs.CONTENDER)
        .with_command(*command)
        .with_user("")
    )
