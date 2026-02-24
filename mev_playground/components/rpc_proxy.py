"""JSON-RPC proxy service for routing contender requests to rbuilder + Reth."""

from pathlib import Path

from mev_playground.service import Service
from mev_playground.config import StaticIPs, StaticPorts

DEFAULT_IMAGE = "python:3.12-slim"
SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "rpc_proxy.py"


def rpc_proxy_service(
    builder_url: str,
    rpc_url: str = f"http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}",
    name: str = "rpc-proxy-1",
    static_ip: str = StaticIPs.RPC_PROXY_1,
    port: int = StaticPorts.RPC_PROXY,
    image: str = DEFAULT_IMAGE,
) -> Service:
    """Create an RPC proxy service.

    Routes eth_sendBundle/eth_sendRawTransaction to the builder,
    and all other JSON-RPC methods to Reth.
    """
    return (
        Service(name)
        .with_image(image)
        .with_static_ip(static_ip)
        .with_command("python", "/app/rpc_proxy.py")
        .with_env(
            BUILDER_URL=builder_url,
            RPC_URL=rpc_url,
            PROXY_PORT=str(port),
        )
        .with_mount("/app", str(SCRIPT_PATH.parent.resolve()), read_only=True)
    )
