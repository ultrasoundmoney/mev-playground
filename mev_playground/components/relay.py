"""Ultrasound relay component."""

from pathlib import Path

from mev_playground.components.base import Component, ContainerConfig
from mev_playground.config import (
    StaticIPs,
    StaticPorts,
    PlaygroundConfig,
    DEFAULT_MEV_SECRET_KEY,
    DEFAULT_MEV_PUBKEY,
    GENESIS_FORK_VERSION,
    BELLATRIX_FORK_VERSION,
    CAPELLA_FORK_VERSION,
    DENEB_FORK_VERSION,
    ELECTRA_FORK_VERSION,
    FULU_FORK_VERSION,
)


class UltrasoundRelayComponent(Component):
    """Ultrasound relay."""

    def __init__(
        self,
        data_dir: Path,
        config: PlaygroundConfig,
        genesis_timestamp: int,
        genesis_validators_root: str,
    ):
        super().__init__(data_dir)
        self.config = config
        self.genesis_timestamp = genesis_timestamp
        self.genesis_validators_root = genesis_validators_root

    @property
    def name(self) -> str:
        return "mev-ultrasound-relay"

    def get_container_config(self) -> ContainerConfig:
        # Build environment variables with static IPs
        environment = {
            # Database connections (static IPs)
            "MEV_DATABASE_URL": f"postgres://postgres:postgres@{StaticIPs.MEVDB}:{StaticPorts.POSTGRES}/postgres?sslmode=disable",
            "LOCAL_DATABASE_URL": f"postgres://postgres:postgres@{StaticIPs.LOCALDB}:{StaticPorts.POSTGRES}/postgres?sslmode=disable",
            "GLOBAL_DATABASE_URL": f"postgres://postgres:postgres@{StaticIPs.GLOBALDB}:{StaticPorts.POSTGRES}/postgres?sslmode=disable",
            "REDIS_URI": f"{StaticIPs.REDIS}:{StaticPorts.REDIS}",
            "REDIS_READ_URI": f"{StaticIPs.REDIS}:{StaticPorts.REDIS}",

            # Node connections (static IPs)
            "CONSENSUS_NODES": f"http://{StaticIPs.LIGHTHOUSE_BN}:{StaticPorts.LIGHTHOUSE_HTTP}",
            "EXECUTION_CLIENT_URLS": f"http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}",
            "BLOCKSIM_URI": f"http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}",

            # Relay identity
            "RELAY_SECRET_KEY": DEFAULT_MEV_SECRET_KEY,
            "PRIVATE_ROUTE_AUTH_TOKEN": "localdevtoken",
            "ADMIN_TOKEN": "localdevtoken",

            # General config
            "GEO": "rbx",
            "BIND_IP_ADDR": "0.0.0.0",
            "API_TIMEOUT": "10000",
            "TOKIO_WORKER_THREADS": "4",
            "LOG_JSON": "false",
            "RUST_LOG": "info",

            # Devnet tuning - skip block simulation since Reth doesn't have flashbots validation
            "TOP_BID_DEBOUNCE_MS_LOCAL": "2",
            "SKIP_SIM_PROBABILITY": "1.0",
            "FORCED_TIMEOUT_MAX_BID_VALUE": "0",
            "X_TIMEOUT_HEADER_CORRECTION": "1500",  # Respond 1.5s before timeout to ensure delivery
            "ADJUSTMENT_LOOKBACK_MS": "50",
            "ADJUSTMENT_MIN_DELTA": "0",
            "SKIP_SIMULATION": "true",
            "DISABLE_BLOCK_SIMULATION": "true",
            "FORCE_FAST_START": "true", # Required for fast start up

            # Feature flags
            "FF_ENABLE_TOP_BID_GOSSIP": "false",
            "FF_LOWBALL_AMOUNT": "1",
            "FF_ENABLE_V3_SUBMISSIONS": "false",
            "FF_ENABLE_DEHYDRATED_SUBMISSIONS": "false",
            "FF_PRIMEV_ENABLED": "false",
            "FF_PRIMEV_ENFORCE": "false",

            # Network config
            "NETWORK": "custom",
            "GENESIS_TIMESTAMP": str(self.genesis_timestamp),
            "GENESIS_VALIDATORS_ROOT": self.genesis_validators_root,
            "GENESIS_FORK_VERSION": GENESIS_FORK_VERSION,
            "BELLATRIX_FORK_VERSION": BELLATRIX_FORK_VERSION,
            "BELLATRIX_FORK_EPOCH": "0",
            "CAPELLA_FORK_VERSION": CAPELLA_FORK_VERSION,
            "CAPELLA_FORK_EPOCH": "0",
            "DENEB_FORK_VERSION": DENEB_FORK_VERSION,
            "DENEB_FORK_EPOCH": "0",
            "ELECTRA_FORK_VERSION": ELECTRA_FORK_VERSION,
            "ELECTRA_FORK_EPOCH": "0",  # Electra from genesis
            "FULU_FORK_VERSION": FULU_FORK_VERSION,
            "FULU_FORK_EPOCH": "18446744073709551615",  # Far future (max uint64)

            # Telegram (disabled)
            "TELEGRAM_API_KEY": "",
            "TELEGRAM_CHANNEL_ID": "",
        }

        # Add any extra environment variables from config
        environment.update(self.config.mev.relay.extra_env)

        return ContainerConfig(
            name=self.name,
            image=self.config.mev.relay.image,
            static_ip=StaticIPs.RELAY,
            environment=environment,
            ports={
                StaticPorts.RELAY_HTTP: StaticPorts.RELAY_HTTP,
            },
            healthcheck={
                "test": [
                    "CMD-SHELL",
                    # Use bash explicitly for /dev/tcp support
                    f"bash -c 'echo >/dev/tcp/localhost/{StaticPorts.RELAY_HTTP}' 2>/dev/null || exit 1",
                ],
                "interval": 5000000000,  # 5 seconds
                "timeout": 3000000000,   # 3 seconds
                "retries": 60,           # More retries to allow for genesis wait
                "start_period": 10000000000,  # 60 seconds to allow genesis time to pass
            },
            depends_on=["redis", "mevdb", "localdb", "globaldb", "lighthouse-bn", "reth"],
            # Relay uses supervisord which requires root to drop privileges
            user="root",
        )

    @property
    def url(self) -> str:
        return f"http://{StaticIPs.RELAY}:{StaticPorts.RELAY_HTTP}"

    @property
    def pubkey_url(self) -> str:
        """URL with pubkey prefix for mev-boost."""
        return f"http://{DEFAULT_MEV_PUBKEY}@{StaticIPs.RELAY}:{StaticPorts.RELAY_HTTP}"
