"""MEV-Boost service."""

from mev_playground.service import Service
from mev_playground.config import (
    StaticIPs,
    StaticPorts,
    PlaygroundConfig,
    DEFAULT_MEV_PUBKEY,
    GENESIS_FORK_VERSION,
)


def mev_boost_service(config: PlaygroundConfig, genesis_timestamp: int) -> Service:
    """Create a MEV-Boost sidecar service."""
    relay_url = f"http://{DEFAULT_MEV_PUBKEY}@{StaticIPs.RELAY}:{StaticPorts.RELAY_HTTP}"

    command = [
        "-addr", f"0.0.0.0:{StaticPorts.MEV_BOOST}",
        "-relay", relay_url,
        "-relay-check",
        "-genesis-fork-version", GENESIS_FORK_VERSION,
        "-genesis-timestamp", str(genesis_timestamp),
        "-request-timeout-getheader", "2900",  # 2.9s timeout (lighthouse max is 3s)
        "-request-timeout-getpayload", "4000",  # 4s timeout for getPayload
        "-request-timeout-regval", "6000",  # 6s timeout for registerValidator
        "-loglevel", "debug",
    ]

    return (
        Service("mev-boost")
        .with_image(config.mev.boost.image)
        .with_static_ip(StaticIPs.MEV_BOOST)
        .with_command(*command)
        .with_port(StaticPorts.MEV_BOOST, StaticPorts.MEV_BOOST)
        .with_healthcheck(
            test=[
                "CMD-SHELL",
                f"wget -q --spider http://localhost:{StaticPorts.MEV_BOOST}/ || exit 1",
            ],
            interval=5000000000,
            timeout=3000000000,
            retries=10,
            start_period=5000000000,
        )
        .with_depends_on("mev-ultrasound-relay")
    )
