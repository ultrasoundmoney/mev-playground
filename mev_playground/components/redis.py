"""Redis service for relay caching."""

from mev_playground.service import Service
from mev_playground.config import StaticIPs


def redis_service() -> Service:
    """Create a Redis cache service for the relay."""
    return (
        Service("redis")
        .with_image("redis:7-alpine")
        .with_static_ip(StaticIPs.REDIS)
        .with_command("redis-server", "--appendonly", "no", "--save", "")
        .with_healthcheck(
            test=["CMD", "redis-cli", "ping"],
            interval=3000000000,
            timeout=2000000000,
            retries=5,
            start_period=3000000000,
        )
    )
