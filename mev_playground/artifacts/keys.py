"""BLS validator key generation using eth2-val-tools Docker container.

Uses the same approach as Kurtosis ethereum-package to generate validator
keystores from a BIP39 mnemonic.
"""

import shutil
import tempfile
from pathlib import Path

import docker
import yaml
from docker.types import Mount


# Default password used for all keystores
DEFAULT_SECRET = "secret"

# Default eth2-val-tools image
DEFAULT_ETH2_VAL_TOOLS_IMAGE = "protolambda/eth2-val-tools:latest"

# Default mnemonic (Kurtosis default)
DEFAULT_MNEMONIC = "giant issue aisle success illegal bike spike question tent bar rely arctic volcano long crawl hungry vocal artwork sniff fantasy very lucky have athlete"


def generate_validator_keystores(
    output_dir: Path,
    mnemonic: str = DEFAULT_MNEMONIC,
    count: int = 100,
    start_index: int = 0,
    password: str = DEFAULT_SECRET,
    image: str = DEFAULT_ETH2_VAL_TOOLS_IMAGE,
    verbose: bool = False,
) -> None:
    """Generate validator keystores using eth2-val-tools Docker container.

    This uses the same approach as Kurtosis ethereum-package to generate
    validator keystores from a BIP39 mnemonic.

    Args:
        output_dir: Directory to write validator files
        mnemonic: BIP39 mnemonic for key derivation
        count: Number of validators to generate
        start_index: Starting validator index
        password: Password for keystores
        image: Docker image for eth2-val-tools
        verbose: Print verbose output
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    client = docker.from_env()

    # Pull image if needed
    try:
        client.images.get(image)
    except docker.errors.ImageNotFound:
        if verbose:
            print(f"Pulling {image}...")
        client.images.pull(image)

    # Create temp directory for output
    # eth2-val-tools requires the output directory to NOT exist, but parent must exist
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Mount parent dir, let tool create 'keystores' subdirectory
        keystores_output = tmp_path / "keystores"
        # Do NOT create keystores_output - the tool wants to create it itself

        # Run eth2-val-tools to generate keystores
        # The container entrypoint is eth2-val-tools, so we just pass subcommand and args
        command = [
            "keystores",
            "--insecure",
            "--prysm-pass", password,
            "--out-loc", "/parent/keystores",  # Tool will create this directory
            "--source-mnemonic", mnemonic,
            "--source-min", str(start_index),
            "--source-max", str(start_index + count),
        ]

        if verbose:
            print(f"Running eth2-val-tools to generate {count} keystores...")

        try:
            result = client.containers.run(
                image=image,
                command=command,
                mounts=[
                    Mount(
                        target="/parent",
                        source=str(tmp_path),
                        type="bind",
                    ),
                ],
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
            )

            if verbose:
                print(f"eth2-val-tools output:\n{result.decode('utf-8')}")

        except docker.errors.ContainerError as e:
            raise RuntimeError(
                f"Failed to generate validator keystores: "
                f"{e.stderr.decode('utf-8') if e.stderr else str(e)}"
            )

        # eth2-val-tools outputs to /output/keys and /output/secrets
        keys_dir = keystores_output / "keys"
        secrets_dir_src = keystores_output / "secrets"

        if not keys_dir.exists():
            raise RuntimeError(
                f"Keystores not generated. Output directory contents: "
                f"{list(keystores_output.iterdir())}"
            )

        # Create output structure for Lighthouse
        keystores_dir = output_dir / "keystores"
        secrets_dir = output_dir / "secrets"
        keystores_dir.mkdir(exist_ok=True)
        secrets_dir.mkdir(exist_ok=True)

        # Copy keystores to Lighthouse format
        # eth2-val-tools creates: keys/0x<pubkey>/voting-keystore.json
        # We need: keystores/validator_N/voting-keystore.json
        validator_definitions = []

        for idx, keystore_dir in enumerate(sorted(keys_dir.iterdir())):
            if not keystore_dir.is_dir():
                continue

            pubkey = keystore_dir.name  # 0x<pubkey>
            validator_idx = start_index + idx

            # Copy keystore
            src_keystore = keystore_dir / "voting-keystore.json"
            dst_keystore_dir = keystores_dir / f"validator_{validator_idx}"
            dst_keystore_dir.mkdir(exist_ok=True)
            shutil.copy(src_keystore, dst_keystore_dir / "voting-keystore.json")

            # Copy secret (password file)
            src_secret = secrets_dir_src / pubkey
            if src_secret.exists():
                shutil.copy(src_secret, secrets_dir / f"validator_{validator_idx}")
            else:
                # Write password if secret file doesn't exist
                (secrets_dir / f"validator_{validator_idx}").write_text(password)

            # Add to validator definitions
            validator_definitions.append({
                "enabled": True,
                "voting_public_key": pubkey,
                "type": "local_keystore",
                "voting_keystore_path": f"/data/validators/keystores/validator_{validator_idx}/voting-keystore.json",
                "voting_keystore_password_path": f"/data/validators/secrets/validator_{validator_idx}",
            })

        # Write validator definitions for Lighthouse
        with open(output_dir / "validator_definitions.yml", "w") as f:
            yaml.dump(validator_definitions, f)

        if verbose:
            print(f"Generated {len(validator_definitions)} validator keystores in {output_dir}")
