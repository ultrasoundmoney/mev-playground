"""Service definitions for MEV Playground."""

from mev_playground.components.base import Service
from mev_playground.components.reth import reth_service
from mev_playground.components.lighthouse import lighthouse_beacon_service, lighthouse_validator_service
from mev_playground.components.mev_boost import mev_boost_service
from mev_playground.components.postgres import postgres_service, create_relay_databases
from mev_playground.components.redis import redis_service
from mev_playground.components.relay import relay_service
from mev_playground.components.rbuilder import rbuilder_service
from mev_playground.components.dora import dora_service
from mev_playground.components.contender import contender_service

__all__ = [
    "Service",
    "reth_service",
    "lighthouse_beacon_service",
    "lighthouse_validator_service",
    "mev_boost_service",
    "postgres_service",
    "create_relay_databases",
    "redis_service",
    "relay_service",
    "rbuilder_service",
    "dora_service",
    "contender_service",
]
