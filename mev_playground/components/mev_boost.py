"""MEV-Boost component."""

from pathlib import Path

from mev_playground.components.base import Component, ContainerConfig
from mev_playground.config import (
    StaticIPs,
    StaticPorts,
    PlaygroundConfig,
    DEFAULT_MEV_PUBKEY,
    GENESIS_FORK_VERSION,
)


class MEVBoostComponent(Component):
    """MEV-Boost sidecar."""

    def __init__(self, data_dir: Path, config: PlaygroundConfig, genesis_timestamp: int):
        super().__init__(data_dir)
        self.config = config
        self.genesis_timestamp = genesis_timestamp

    @property
    def name(self) -> str:
        return "mev-boost"

    def get_container_config(self) -> ContainerConfig:
        # Relay URL format: pubkey@host:port
        relay_url = f"http://{DEFAULT_MEV_PUBKEY}@{StaticIPs.RELAY}:{StaticPorts.RELAY_HTTP}"

        command = [
            "-addr", f"0.0.0.0:{StaticPorts.MEV_BOOST}",
            "-relay", relay_url,
            "-relay-check",
            "-genesis-fork-version", GENESIS_FORK_VERSION,
            "-genesis-timestamp", str(self.genesis_timestamp),
            "-request-timeout-getheader", "2900",  # 2.9s timeout (lighthouse max is 3s)
            "-request-timeout-getpayload", "4000",  # 4s timeout for getPayload
            "-request-timeout-regval", "6000",  # 6s timeout for registerValidator
            "-loglevel", "debug",
        ]

        return ContainerConfig(
            name=self.name,
            image=self.config.mev.boost.image,
            static_ip=StaticIPs.MEV_BOOST,
            command=command,
            ports={
                StaticPorts.MEV_BOOST: StaticPorts.MEV_BOOST,
            },
            healthcheck={
                "test": [
                    "CMD-SHELL",
                    # Use wget for health check (available in alpine-based images)
                    f"wget -q --spider http://localhost:{StaticPorts.MEV_BOOST}/ || exit 1",
                ],
                "interval": 5000000000,
                "timeout": 3000000000,
                "retries": 10,
                "start_period": 5000000000,
            },
            depends_on=["mev-ultrasound-relay"],
        )

    @property
    def url(self) -> str:
        return f"http://{StaticIPs.MEV_BOOST}:{StaticPorts.MEV_BOOST}"
