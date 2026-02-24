"""Genesis generation using ethpandaops/ethereum-genesis-generator.

This module generates EL and CL genesis data using the same Docker-based approach
as Kurtosis ethereum-package. It runs the ethereum-genesis-generator container
with a values.env configuration file to produce coordinated genesis artifacts.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import docker
from docker.types import Mount


# Default genesis generator image (same as Kurtosis)
DEFAULT_GENESIS_GENERATOR_IMAGE = "ethpandaops/ethereum-genesis-generator:5.2.0"

# Default mnemonic (same as Kurtosis)
DEFAULT_MNEMONIC = "giant issue aisle success illegal bike spike question tent bar rely arctic volcano long crawl hungry vocal artwork sniff fantasy very lucky have athlete"

# Deposit contract address
DEPOSIT_CONTRACT_ADDRESS = "0x4242424242424242424242424242424242424242"

# Fork versions (matching Kurtosis ethereum-package)
GENESIS_FORK_VERSION = "0x10000038"
ALTAIR_FORK_VERSION = "0x20000038"
BELLATRIX_FORK_VERSION = "0x30000038"
CAPELLA_FORK_VERSION = "0x40000038"
DENEB_FORK_VERSION = "0x50000038"
ELECTRA_FORK_VERSION = "0x60000038"
FULU_FORK_VERSION = "0x70000038"

# Far future epoch (disabled forks)
FAR_FUTURE_EPOCH = 18446744073709551615

# Disperse contract (from https://github.com/omniaprotocol/disperse.app)
# Runtime bytecode fetched from mainnet deployment at 0xD152f549545093347A162Dce210e7293f1452150
DISPERSE_CONTRACT_ADDRESS = "0xD152f549545093347A162Dce210e7293f1452150"
DISPERSE_CONTRACT_BYTECODE = "0x608060405260043610610057576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff16806351ba162c1461005c578063c73a2d60146100cf578063e63d38ed14610142575b600080fd5b34801561006857600080fd5b506100cd600480360381019080803573ffffffffffffffffffffffffffffffffffffffff169060200190929190803590602001908201803590602001919091929391929390803590602001908201803590602001919091929391929390505050610188565b005b3480156100db57600080fd5b50610140600480360381019080803573ffffffffffffffffffffffffffffffffffffffff169060200190929190803590602001908201803590602001919091929391929390803590602001908201803590602001919091929391929390505050610309565b005b6101866004803603810190808035906020019082018035906020019190919293919293908035906020019082018035906020019190919293919293905050506105b0565b005b60008090505b84849050811015610301578573ffffffffffffffffffffffffffffffffffffffff166323b872dd3387878581811015156101c457fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1686868681811015156101ef57fe5b905060200201356040518463ffffffff167c0100000000000000000000000000000000000000000000000000000000028152600401808473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020018373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020018281526020019350505050602060405180830381600087803b1580156102ae57600080fd5b505af11580156102c2573d6000803e3d6000fd5b505050506040513d60208110156102d857600080fd5b810190808051906020019092919050505015156102f457600080fd5b808060010191505061018e565b505050505050565b60008060009150600090505b8585905081101561034657838382818110151561032e57fe5b90506020020135820191508080600101915050610315565b8673ffffffffffffffffffffffffffffffffffffffff166323b872dd3330856040518463ffffffff167c0100000000000000000000000000000000000000000000000000000000028152600401808473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020018373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020018281526020019350505050602060405180830381600087803b15801561041d57600080fd5b505af1158015610431573d6000803e3d6000fd5b505050506040513d602081101561044757600080fd5b8101908080519060200190929190505050151561046357600080fd5b600090505b858590508110156105a7578673ffffffffffffffffffffffffffffffffffffffff1663a9059cbb878784818110151561049d57fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1686868581811015156104c857fe5b905060200201356040518363ffffffff167c0100000000000000000000000000000000000000000000000000000000028152600401808373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200182815260200192505050602060405180830381600087803b15801561055457600080fd5b505af1158015610568573d6000803e3d6000fd5b505050506040513d602081101561057e57600080fd5b8101908080519060200190929190505050151561059a57600080fd5b8080600101915050610468565b50505050505050565b600080600091505b858590508210156106555785858381811015156105d157fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff166108fc858585818110151561061557fe5b905060200201359081150290604051600060405180830381858888f19350505050158015610647573d6000803e3d6000fd5b5081806001019250506105b8565b3073ffffffffffffffffffffffffffffffffffffffff1631905060008111156106c0573373ffffffffffffffffffffffffffffffffffffffff166108fc829081150290604051600060405180830381858888f193505050501580156106be573d6000803e3d6000fd5b505b5050505050505600a165627a7a72305820104eaf57909eb0d29f37ba9e3196e8e88438f83546136cf61270ca5d3b491e160029"

# Default preloaded contracts (Disperse contract for block merging revenue distribution)
DEFAULT_PRELOADED_CONTRACTS = {
    DISPERSE_CONTRACT_ADDRESS: {
        "balance": "0x0",
        "code": DISPERSE_CONTRACT_BYTECODE,
        "storage": {},
        "nonce": "0x1",
    }
}

# Hardhat/Foundry default accounts for prefunding
DEFAULT_PREFUNDED_ACCOUNTS = {
    "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266": {"balance": "0x21e19e0c9bab2400000"},  # 10000 ETH
    "0x70997970C51812dc3A010C7d01b50e0d17dc79C8": {"balance": "0x21e19e0c9bab2400000"},
    "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC": {"balance": "0x21e19e0c9bab2400000"},
    "0x90F79bf6EB2c4f870365E785982E1f101E93b906": {"balance": "0x21e19e0c9bab2400000"},
    "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65": {"balance": "0x21e19e0c9bab2400000"},
    "0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc": {"balance": "0x21e19e0c9bab2400000"},
    "0x976EA74026E726554dB657fA54763abd0C3a0aa9": {"balance": "0x21e19e0c9bab2400000"},
    "0x14dC79964da2C08b23698B3D3cc7Ca32193d9955": {"balance": "0x21e19e0c9bab2400000"},
    "0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f": {"balance": "0x21e19e0c9bab2400000"},
    "0xa0Ee7A142d267C1f36714E4a8F75612F20a79720": {"balance": "0x21e19e0c9bab2400000"},
}


@dataclass
class GenesisGeneratorConfig:
    """Configuration for genesis generation."""

    # Network parameters
    chain_id: int = 3151908  # Kurtosis default
    preset: str = "mainnet"

    # Timing
    genesis_delay: int = 30  # Seconds from now until genesis
    seconds_per_slot: int = 12
    slot_duration_ms: int = 12000

    # Validators
    num_validators: int = 100
    mnemonic: str = DEFAULT_MNEMONIC
    validator_balance: int = 32  # ETH per validator

    # Fork epochs (0 = enabled at genesis, FAR_FUTURE_EPOCH = disabled)
    altair_fork_epoch: int = 0
    bellatrix_fork_epoch: int = 0
    capella_fork_epoch: int = 0
    deneb_fork_epoch: int = 0
    electra_fork_epoch: int = 0
    fulu_fork_epoch: int = FAR_FUTURE_EPOCH  # Disabled by default

    # EL parameters
    genesis_gas_limit: int = 30000000

    # Withdrawal configuration
    withdrawal_type: str = "0x01"  # ETH1 address withdrawal (0x00 = BLS, 0x01 = ETH1)
    withdrawal_address: str = "0x8943545177806ED17B9F23F0a21ee5948eCaa776"

    # Additional parameters
    max_per_epoch_activation_churn_limit: int = 8
    churn_limit_quotient: int = 65536
    ejection_balance: int = 16000000000  # 16 ETH in Gwei
    eth1_follow_distance: int = 2048
    min_validator_withdrawability_delay: int = 256
    shard_committee_period: int = 256

    # Prefunded accounts
    prefunded_accounts: dict = field(default_factory=lambda: DEFAULT_PREFUNDED_ACCOUNTS.copy())

    # Additional preloaded contracts (includes Disperse contract by default)
    additional_preloaded_contracts: dict = field(default_factory=lambda: DEFAULT_PRELOADED_CONTRACTS.copy())

    # Docker image
    genesis_generator_image: str = DEFAULT_GENESIS_GENERATOR_IMAGE


@dataclass
class GenesisData:
    """Container for generated genesis data."""

    genesis_time: int
    genesis_validators_root: str
    el_genesis_path: Path
    cl_genesis_ssz_path: Path
    cl_config_path: Path
    deploy_block_path: Path
    deposit_contract_block_path: Path


def _generate_values_env(config: GenesisGeneratorConfig, genesis_timestamp: int) -> str:
    """Generate the values.env file content for ethereum-genesis-generator.

    Args:
        config: Genesis configuration
        genesis_timestamp: Unix timestamp for genesis

    Returns:
        values.env file content
    """
    # Convert prefunded accounts to the format expected by the generator
    prefunded_accounts_json = json.dumps(config.prefunded_accounts)

    lines = [
        f'export PRESET_BASE="{config.preset}"',
        f'export CHAIN_ID="{config.chain_id}"',
        f'export DEPOSIT_CONTRACT_ADDRESS="{DEPOSIT_CONTRACT_ADDRESS}"',
        f'export EL_AND_CL_MNEMONIC="{config.mnemonic}"',
        'export CL_EXEC_BLOCK="0"',
        f'export SLOT_DURATION_IN_SECONDS={config.seconds_per_slot}',
        f'export SLOT_DURATION_MS={config.slot_duration_ms}',
        'export DEPOSIT_CONTRACT_BLOCK="0x0000000000000000000000000000000000000000000000000000000000000000"',
        f'export NUMBER_OF_VALIDATORS={config.num_validators}',
        f'export GENESIS_FORK_VERSION="{GENESIS_FORK_VERSION}"',
        f'export ALTAIR_FORK_VERSION="{ALTAIR_FORK_VERSION}"',
        f'export ALTAIR_FORK_EPOCH="{config.altair_fork_epoch}"',
        f'export BELLATRIX_FORK_VERSION="{BELLATRIX_FORK_VERSION}"',
        f'export BELLATRIX_FORK_EPOCH="{config.bellatrix_fork_epoch}"',
        f'export CAPELLA_FORK_VERSION="{CAPELLA_FORK_VERSION}"',
        f'export CAPELLA_FORK_EPOCH="{config.capella_fork_epoch}"',
        f'export DENEB_FORK_VERSION="{DENEB_FORK_VERSION}"',
        f'export DENEB_FORK_EPOCH="{config.deneb_fork_epoch}"',
        f'export ELECTRA_FORK_VERSION="{ELECTRA_FORK_VERSION}"',
        f'export ELECTRA_FORK_EPOCH="{config.electra_fork_epoch}"',
        f'export FULU_FORK_VERSION="{FULU_FORK_VERSION}"',
        f'export FULU_FORK_EPOCH="{config.fulu_fork_epoch}"',
        # Disabled forks (use far future epoch)
        f'export GLOAS_FORK_VERSION="0x80000038"',
        f'export GLOAS_FORK_EPOCH="{FAR_FUTURE_EPOCH}"',
        f'export EIP7805_FORK_VERSION="0x90000038"',
        f'export EIP7805_FORK_EPOCH="{FAR_FUTURE_EPOCH}"',
        f'export EIP7441_FORK_VERSION="0xa0000038"',
        f'export EIP7441_FORK_EPOCH="{FAR_FUTURE_EPOCH}"',
        f'export WITHDRAWAL_TYPE="{config.withdrawal_type}"',  # Must be hex like 0x00 or 0x01
        f'export WITHDRAWAL_ADDRESS="{config.withdrawal_address}"',
        f'export VALIDATOR_BALANCE="{config.validator_balance * 1000000000}"',  # Convert ETH to Gwei
        f'export GENESIS_TIMESTAMP={genesis_timestamp}',
        'export GENESIS_DELAY=0',  # Delay already calculated in timestamp
        f'export GENESIS_GASLIMIT={config.genesis_gas_limit}',
        f'export MAX_PER_EPOCH_ACTIVATION_CHURN_LIMIT={config.max_per_epoch_activation_churn_limit}',
        f'export CHURN_LIMIT_QUOTIENT={config.churn_limit_quotient}',
        f'export EJECTION_BALANCE={config.ejection_balance}',
        f'export ETH1_FOLLOW_DISTANCE={config.eth1_follow_distance}',
        'export SHADOW_FORK_FILE=""',
        f'export MIN_VALIDATOR_WITHDRAWABILITY_DELAY={config.min_validator_withdrawability_delay}',
        f'export SHARD_COMMITTEE_PERIOD={config.shard_committee_period}',
        # PeerDAS/Fulu parameters (defaults)
        'export DATA_COLUMN_SIDECAR_SUBNET_COUNT=128',
        'export SAMPLES_PER_SLOT=8',
        'export CUSTODY_REQUIREMENT=4',
        # Blob parameters
        'export MAX_BLOBS_PER_BLOCK_ELECTRA=9',
        'export TARGET_BLOBS_PER_BLOCK_ELECTRA=6',
        'export MAX_REQUEST_BLOCKS_DENEB=128',
        'export MAX_REQUEST_BLOB_SIDECARS_ELECTRA=1152',
        'export BASEFEE_UPDATE_FRACTION_ELECTRA=5007716',
        # Additional contracts file path (inside container - we copy it to /config)
        'export ADDITIONAL_PRELOADED_CONTRACTS=/config/additional-contracts.json',
        f"export EL_PREMINE_ADDRS='{prefunded_accounts_json}'",
        'export MAX_PAYLOAD_SIZE=10485760',
        # Blob parameter overrides (disabled)
        f'export BPO_1_EPOCH="{FAR_FUTURE_EPOCH}"',
        'export BPO_1_MAX_BLOBS=0',
        'export BPO_1_TARGET_BLOBS=0',
        'export BPO_1_BASE_FEE_UPDATE_FRACTION=0',
        f'export BPO_2_EPOCH="{FAR_FUTURE_EPOCH}"',
        'export BPO_2_MAX_BLOBS=0',
        'export BPO_2_TARGET_BLOBS=0',
        'export BPO_2_BASE_FEE_UPDATE_FRACTION=0',
        f'export BPO_3_EPOCH="{FAR_FUTURE_EPOCH}"',
        'export BPO_3_MAX_BLOBS=0',
        'export BPO_3_TARGET_BLOBS=0',
        'export BPO_3_BASE_FEE_UPDATE_FRACTION=0',
        f'export BPO_4_EPOCH="{FAR_FUTURE_EPOCH}"',
        'export BPO_4_MAX_BLOBS=0',
        'export BPO_4_TARGET_BLOBS=0',
        'export BPO_4_BASE_FEE_UPDATE_FRACTION=0',
        f'export BPO_5_EPOCH="{FAR_FUTURE_EPOCH}"',
        'export BPO_5_MAX_BLOBS=0',
        'export BPO_5_TARGET_BLOBS=0',
        'export BPO_5_BASE_FEE_UPDATE_FRACTION=0',
        'export MIN_EPOCHS_FOR_DATA_COLUMN_SIDECARS_REQUESTS=4096',
        'export MIN_EPOCHS_FOR_BLOCK_REQUESTS=33024',
        # Timing parameters for GLOAS (not used but required)
        'export ATTESTATION_DUE_BPS_GLOAS=4000',
        'export AGGREGATE_DUE_BPS_GLOAS=8000',
        'export SYNC_MESSAGE_DUE_BPS_GLOAS=4000',
        'export CONTRIBUTION_DUE_BPS_GLOAS=8000',
        'export PAYLOAD_ATTESTATION_DUE_BPS=5000',
        'export VIEW_FREEZE_CUTOFF_BPS=6000',
        'export INCLUSION_LIST_SUBMISSION_DUE_BPS=5000',
        'export PROPOSER_INCLUSION_LIST_CUTOFF_BPS=6000',
    ]

    return '\n'.join(lines) + '\n'


def generate_genesis(
    output_dir: Path,
    config: Optional[GenesisGeneratorConfig] = None,
    genesis_time: Optional[int] = None,
    verbose: bool = False,
) -> GenesisData:
    """Generate EL and CL genesis data using ethereum-genesis-generator.

    This function runs the ethpandaops/ethereum-genesis-generator Docker container
    to produce coordinated genesis artifacts for both the execution and consensus
    layers, following the same approach as Kurtosis ethereum-package.

    Args:
        output_dir: Directory to write genesis artifacts
        config: Genesis configuration (uses defaults if not provided)
        genesis_time: Override genesis timestamp (defaults to now + genesis_delay)
        verbose: Print verbose output

    Returns:
        GenesisData containing paths to all generated artifacts

    Raises:
        RuntimeError: If genesis generation fails
    """
    config = config or GenesisGeneratorConfig()

    # Calculate genesis timestamp
    if genesis_time is None:
        genesis_time = int(time.time()) + config.genesis_delay

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create a temporary directory for the configuration in the current directory
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp_dir:
        tmp_path = Path(tmp_dir).resolve()

        # Write values.env
        values_env_content = _generate_values_env(config, genesis_time)
        values_env_path = tmp_path / "values.env"
        values_env_path.write_text(values_env_content)

        if verbose:
            print(f"Generated values.env:\n{values_env_content}")

        # Write additional-contracts.json
        contracts_json = json.dumps(config.additional_preloaded_contracts)
        contracts_path = tmp_path / "additional-contracts.json"
        contracts_path.write_text(contracts_json)

        # Create output subdirectory for container output
        container_output = tmp_path / "output"
        container_output.mkdir()

        # Run the genesis generator container
        client = docker.from_env()

        # Pull image if needed
        try:
            client.images.get(config.genesis_generator_image)
        except docker.errors.ImageNotFound:
            if verbose:
                print(f"Pulling {config.genesis_generator_image}...")
            client.images.pull(config.genesis_generator_image)

        # Run the container
        # The container has templates at /config/cl/ and /config/el/
        # It reads values.env from /config/values.env and additional-contracts from the path specified
        # We mount our config files directly to avoid permission issues when running as non-root
        if verbose:
            print("Running genesis generator...")

        print(f"values env path: {str(values_env_path.resolve())}")
        print(f"contracts path: {str(contracts_path.resolve())}")
        print(f"container output path: {str(container_output.resolve())}")
        try:
            container = client.containers.run(
                image=config.genesis_generator_image,
                command=["all"],
                mounts=[
                    Mount(
                        target="/config/values.env",
                        source=str(values_env_path.resolve()),
                        type="bind",
                        read_only=True,
                    ),
                    Mount(
                        target="/config/additional-contracts.json",
                        source=str(contracts_path.resolve()),
                        type="bind",
                        read_only=True,
                    ),
                    Mount(
                        target="/data",
                        source=str(container_output.resolve()),
                        type="bind",
                    ),
                ],
                # Run as current user so files can be cleaned up
                user=f"{os.getuid()}:{os.getgid()}",
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
            )

            if verbose:
                print(f"Container output:\n{container.decode('utf-8')}")

        except docker.errors.ContainerError as e:
            raise RuntimeError(
                f"Genesis generation failed: {e.stderr.decode('utf-8') if e.stderr else str(e)}"
            )

        # The generator outputs to /data/metadata/ and /data/parsed/
        metadata_dir = container_output / "metadata"
        if not metadata_dir.exists():
            raise RuntimeError(
                f"Genesis generation failed: metadata directory not found. "
                f"Container output contents: {list(container_output.iterdir())}"
            )

        # Copy artifacts to output directory
        # EL genesis
        el_genesis_src = metadata_dir / "genesis.json"
        el_genesis_dst = output_dir / "genesis.json"
        if el_genesis_src.exists():
            shutil.copy(el_genesis_src, el_genesis_dst)
        else:
            raise RuntimeError("EL genesis.json not generated")

        # CL genesis state (SSZ)
        cl_genesis_src = metadata_dir / "genesis.ssz"
        cl_genesis_dst = output_dir / "genesis.ssz"
        if cl_genesis_src.exists():
            shutil.copy(cl_genesis_src, cl_genesis_dst)
        else:
            raise RuntimeError("CL genesis.ssz not generated")

        # CL config
        cl_config_src = metadata_dir / "config.yaml"
        cl_config_dst = output_dir / "config.yaml"
        if cl_config_src.exists():
            shutil.copy(cl_config_src, cl_config_dst)
        else:
            raise RuntimeError("CL config.yaml not generated")

        # Genesis validators root
        validators_root_src = metadata_dir / "genesis_validators_root.txt"
        validators_root_dst = output_dir / "genesis_validators_root.txt"
        if validators_root_src.exists():
            shutil.copy(validators_root_src, validators_root_dst)
            genesis_validators_root = validators_root_src.read_text().strip()
        else:
            raise RuntimeError("genesis_validators_root.txt not generated")

        # Deploy block files
        deploy_block_dst = output_dir / "deploy_block.txt"
        deploy_block_dst.write_text("0")

        deposit_contract_block_dst = output_dir / "deposit_contract_block.txt"
        deposit_contract_block_dst.write_text("0")

        # Copy any additional useful files
        for extra_file in ["beaconstate.ssz", "tranches"]:
            src = metadata_dir / extra_file
            if src.exists():
                if src.is_file():
                    shutil.copy(src, output_dir / extra_file)
                else:
                    shutil.copytree(src, output_dir / extra_file, dirs_exist_ok=True)

        # Copy parsed directory if it exists
        parsed_src = container_output / "parsed"
        if parsed_src.exists():
            shutil.copytree(parsed_src, output_dir / "parsed", dirs_exist_ok=True)

        if verbose:
            print(f"Genesis artifacts written to {output_dir}")
            print(f"  Genesis time: {genesis_time}")
            print(f"  Genesis validators root: {genesis_validators_root}")

        return GenesisData(
            genesis_time=genesis_time,
            genesis_validators_root=genesis_validators_root,
            el_genesis_path=el_genesis_dst,
            cl_genesis_ssz_path=cl_genesis_dst,
            cl_config_path=cl_config_dst,
            deploy_block_path=deploy_block_dst,
            deposit_contract_block_path=deposit_contract_block_dst,
        )


def get_genesis_validators_root(genesis_dir: Path) -> str:
    """Read the genesis validators root from a generated genesis directory.

    Args:
        genesis_dir: Directory containing genesis artifacts

    Returns:
        Genesis validators root as hex string (with 0x prefix)
    """
    root_file = genesis_dir / "genesis_validators_root.txt"
    if not root_file.exists():
        raise FileNotFoundError(f"Genesis validators root not found at {root_file}")

    root = root_file.read_text().strip()
    if not root.startswith("0x"):
        root = "0x" + root
    return root


def get_genesis_time(genesis_dir: Path) -> int:
    """Read the genesis timestamp from a generated genesis directory.

    Args:
        genesis_dir: Directory containing genesis artifacts

    Returns:
        Genesis timestamp as Unix epoch seconds
    """
    genesis_file = genesis_dir / "genesis.json"
    if not genesis_file.exists():
        raise FileNotFoundError(f"Genesis file not found at {genesis_file}")

    with open(genesis_file) as f:
        genesis = json.load(f)

    timestamp = genesis["timestamp"]
    # Handle both hex (0x...) and decimal string formats
    if isinstance(timestamp, str):
        if timestamp.startswith("0x"):
            return int(timestamp, 16)
        else:
            return int(timestamp)
    return int(timestamp)
