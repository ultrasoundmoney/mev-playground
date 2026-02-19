"""Redis service for relay caching."""

from mev_playground.components.base import Service
from mev_playground.config import StaticIPs


def redis_service() -> Service:
    """Create a Redis cache service for the relay."""
    return Service(
        name="redis",
        image="redis:7-alpine",
        static_ip=StaticIPs.REDIS,
        command=["redis-server", "--appendonly", "no", "--save", ""],
        healthcheck={
            "test": ["CMD", "redis-cli", "ping"],
            "interval": 3000000000,
            "timeout": 2000000000,
            "retries": 5,
            "start_period": 3000000000,
        },
    )
