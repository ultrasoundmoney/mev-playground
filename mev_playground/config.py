"""Configuration models for MEV Playground."""

import platform
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


def get_rbuilder_image() -> str:
    """Get the rbuilder image for the current architecture."""
    arch = platform.machine().lower()
    if arch in ("arm64", "aarch64"):
        return "ghcr.io/flashbots/rbuilder:latest-linux-arm64"
    else:
        return "ghcr.io/flashbots/rbuilder:latest"


# Static IP addresses for all components
class StaticIPs:
    """Static IP addresses within the Docker network (172.28.0.0/16)."""

    # Core Ethereum stack
    RETH = "172.28.1.1"
    LIGHTHOUSE_BN = "172.28.1.2"
    LIGHTHOUSE_VC = "172.28.1.3"
    MEV_BOOST = "172.28.1.4"

    # Relay infrastructure
    RELAY = "172.28.2.1"
    REDIS = "172.28.2.2"
    MEVDB = "172.28.2.3"
    LOCALDB = "172.28.2.4"
    GLOBALDB = "172.28.2.5"

    # Builder
    RBUILDER = "172.28.3.1"

    # Tools
    DORA = "172.28.4.1"
    CONTENDER = "172.28.4.2"


# Static ports
class StaticPorts:
    """Static port assignments for all components."""

    RETH_HTTP = 8545
    RETH_WS = 8546
    RETH_AUTH = 8551
    RETH_METRICS = 9001
    LIGHTHOUSE_HTTP = 3500
    LIGHTHOUSE_METRICS = 5054
    LIGHTHOUSE_P2P = 9000
    MEV_BOOST = 18550
    RELAY_HTTP = 80
    REDIS = 6379
    POSTGRES = 5432
    RBUILDER_RPC = 8645


# Network configuration
DOCKER_NETWORK_NAME = "mev-playground"
DOCKER_NETWORK_SUBNET = "172.28.0.0/16"

# Fork versions (matching Kurtosis ethereum-package)
GENESIS_FORK_VERSION = "0x10000038"
ALTAIR_FORK_VERSION = "0x20000038"
BELLATRIX_FORK_VERSION = "0x30000038"
CAPELLA_FORK_VERSION = "0x40000038"
DENEB_FORK_VERSION = "0x50000038"
ELECTRA_FORK_VERSION = "0x60000038"
FULU_FORK_VERSION = "0x70000038"

# Default validator mnemonic (same as Kurtosis)
DEFAULT_MNEMONIC = "giant issue aisle success illegal bike spike question tent bar rely arctic volcano long crawl hungry vocal artwork sniff fantasy very lucky have athlete"

# Far future epoch for disabled forks
FAR_FUTURE_EPOCH = 18446744073709551615

# Default MEV keys
DEFAULT_MEV_PUBKEY = "0xa55c1285d84ba83a5ad26420cd5ad3091e49c55a813eee651cd467db38a8c8e63192f47955e9376f6b42f6d190571cb5"
DEFAULT_MEV_SECRET_KEY = "0x607a11b45a7219cc61a3d9c5fd08c7eebd602a6a19a977f8d3771d5711a550f2"

# Default data directory
DEFAULT_DATA_DIR = Path.home() / ".mev_playground"


class NetworkConfig(BaseModel):
    """Network configuration."""

    chain_id: int = 3151908  # Kurtosis default chain ID
    seconds_per_slot: int = 12
    slots_per_epoch: int = 32
    genesis_delay: int = 0  # Seconds from now until genesis

    # Beacon chain preset
    preset: str = "mainnet"

    # Validator mnemonic (BIP39) - used for deterministic key generation
    # Default is the Kurtosis mnemonic for reproducible testing
    mnemonic: str = DEFAULT_MNEMONIC

    # Fork epochs (0 = enabled at genesis, FAR_FUTURE_EPOCH = disabled)
    electra_fork_epoch: int = 0  # Enable Electra at genesis
    fulu_fork_epoch: int = FAR_FUTURE_EPOCH  # Disable Fulu by default

    # Genesis generator Docker image
    genesis_generator_image: str = "ethpandaops/ethereum-genesis-generator:5.2.0"


class ExecutionConfig(BaseModel):
    """Execution client configuration."""

    image: str = "ghcr.io/paradigmxyz/reth:v1.8.2"


class ConsensusConfig(BaseModel):
    """Consensus client configuration."""

    image: str = "sigp/lighthouse:v8.0.0-rc.2"  # Electra support


class ValidatorConfig(BaseModel):
    """Validator configuration."""

    count: int = 100  # Matches pre-generated fixtures from builder-playground


class RelayConfig(BaseModel):
    """Relay configuration."""

    image: str = "turbo-relay-combined:latest"
    extra_env: dict[str, str] = Field(default_factory=dict)


class BuilderConfig(BaseModel):
    """Builder configuration."""

    enabled: bool = True  # Enabled by default with rbuilder
    type: str = "rbuilder"  # or "custom" or "none"
    image: str = Field(default_factory=get_rbuilder_image)
    extra_env: dict[str, str] = Field(default_factory=dict)


class MEVBoostConfig(BaseModel):
    """MEV-Boost configuration."""

    image: str = "flashbots/mev-boost:latest"


class ContenderConfig(BaseModel):
    """Contender transaction spammer configuration."""

    image: str = "flashbots/contender:latest"
    tps: int = 20  # Transactions per second
    extra_args: list[str] = Field(default_factory=list)


class MEVConfig(BaseModel):
    """MEV stack configuration."""

    relay: RelayConfig = Field(default_factory=RelayConfig)
    builder: BuilderConfig = Field(default_factory=BuilderConfig)
    boost: MEVBoostConfig = Field(default_factory=MEVBoostConfig)


class PlaygroundConfig(BaseModel):
    """Complete playground configuration."""

    network: NetworkConfig = Field(default_factory=NetworkConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    consensus: ConsensusConfig = Field(default_factory=ConsensusConfig)
    validators: ValidatorConfig = Field(default_factory=ValidatorConfig)
    mev: MEVConfig = Field(default_factory=MEVConfig)
    contender: ContenderConfig = Field(default_factory=ContenderConfig)
    data_dir: Path = DEFAULT_DATA_DIR

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"

    @property
    def chain_data_dir(self) -> Path:
        return self.data_dir / "data"

    @property
    def config_dir(self) -> Path:
        return self.data_dir / "config"
