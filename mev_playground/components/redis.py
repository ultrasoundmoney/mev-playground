"""Redis component for relay caching."""

from pathlib import Path

from mev_playground.components.base import Component, ContainerConfig
from mev_playground.config import StaticIPs, StaticPorts


class RedisComponent(Component):
    """Redis cache for the relay."""

    def __init__(self, data_dir: Path):
        super().__init__(data_dir)

    @property
    def name(self) -> str:
        return "redis"

    def get_container_config(self) -> ContainerConfig:
        return ContainerConfig(
            name=self.name,
            image="redis:7-alpine",
            static_ip=StaticIPs.REDIS,
            command=["redis-server", "--appendonly", "no", "--save", ""],
            # No host port binding - only accessible within Docker network
            ports={},
            healthcheck={
                "test": ["CMD", "redis-cli", "ping"],
                "interval": 3000000000,
                "timeout": 2000000000,
                "retries": 5,
                "start_period": 3000000000,
            },
        )

    @property
    def url(self) -> str:
        return f"{StaticIPs.REDIS}:{StaticPorts.REDIS}"
