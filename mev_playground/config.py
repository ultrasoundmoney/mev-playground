"""Configuration for MEV Playground."""

import platform
from dataclasses import dataclass, field
from pathlib import Path


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

# Block merging builder accounts (Foundry/Hardhat test accounts)
BUILDER_1_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
BUILDER_1_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
BUILDER_1_COLLATERAL_KEY = "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba"
BUILDER_2_ADDRESS = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
BUILDER_2_PRIVATE_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
BUILDER_2_COLLATERAL_KEY = "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e"

# Block merging relay fee recipient (Foundry/Hardhat test account 2)
RELAY_FEE_RECIPIENT = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

# Disperse contract address (same as mainnet deployment from disperse.app)
DISPERSE_CONTRACT_ADDRESS = "0xD152f549545093347A162Dce210e7293f1452150"

# Default builder collateral map (builder coinbase -> collateral signer private key)
DEFAULT_BUILDER_COLLATERAL_MAP = {
    BUILDER_1_ADDRESS: BUILDER_1_COLLATERAL_KEY,
    BUILDER_2_ADDRESS: BUILDER_2_COLLATERAL_KEY,
}

# Default data directory
DEFAULT_DATA_DIR = Path.home() / ".mev_playground"


@dataclass
class PlaygroundConfig:
    """Playground configuration (CLI-overridable fields only)."""

    data_dir: Path = DEFAULT_DATA_DIR
    relay_image: str = "turbo-relay-combined:latest"
    builder_enabled: bool = True
    builder_image: str = field(default_factory=get_rbuilder_image)

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"
