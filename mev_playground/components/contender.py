"""Contender transaction spammer component."""

from pathlib import Path

from mev_playground.components.base import Component, ContainerConfig
from mev_playground.config import StaticIPs, StaticPorts


class ContenderComponent(Component):
    """Flashbots Contender transaction spammer."""

    def __init__(
        self,
        data_dir: Path,
        tps: int = 20,
        extra_args: list[str] | None = None,
        image: str = "flashbots/contender:latest",
    ):
        super().__init__(data_dir)
        self.tps = tps
        self.extra_args = extra_args or []
        self.image = image

    @property
    def name(self) -> str:
        return "contender"

    def get_container_config(self) -> ContainerConfig:
        # Build command args for contender spam
        # Using 'transfers' subcommand for simple ETH transfers
        command = [
            "spam",
            "--rpc-url", f"http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}",
            "--min-balance", "10 ether",
            "--tps", str(self.tps),
            "--forever",  # Run indefinitely
        ]

        # Add any extra args
        command.extend(self.extra_args)

        # Add the transfers subcommand at the end
        command.append("transfers")

        return ContainerConfig(
            name=self.name,
            image=self.image,
            static_ip=StaticIPs.CONTENDER,
            command=command,
            user="",  # Use image default user (don't override with host user)
            # No healthcheck - Contender runs continuously
        )
