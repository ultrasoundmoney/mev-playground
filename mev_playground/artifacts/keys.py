"""Pre-generated BLS validator keys.

Uses pre-generated deterministic keys (from Prysm interop) embedded as a fixture,
eliminating the need for Docker-based key generation at runtime.
"""

import json
from importlib import resources
from pathlib import Path
from typing import NamedTuple


# Default password used for all keystores (matches builder-playground)
DEFAULT_SECRET = "secret"


class ValidatorKey(NamedTuple):
    """A validator key pair."""

    index: int
    pubkey: str  # hex string without 0x prefix
    privkey: str  # hex string without 0x prefix
    keystore: dict  # EIP-2335 keystore


def _load_pregenerated_keys() -> list[dict]:
    """Load pre-generated BLS keys from the embedded fixture."""
    fixtures_path = Path(__file__).parent / "fixtures" / "bls_keys.json"
    with open(fixtures_path) as f:
        return json.load(f)


# Cache the loaded keys
_PREGENERATED_KEYS: list[dict] | None = None


def get_pregenerated_keys() -> list[dict]:
    """Get all pre-generated BLS keys (100 total)."""
    global _PREGENERATED_KEYS
    if _PREGENERATED_KEYS is None:
        _PREGENERATED_KEYS = _load_pregenerated_keys()
    return _PREGENERATED_KEYS


def get_validator_keys(count: int, start_index: int = 0) -> list[ValidatorKey]:
    """Get validator keys from the pre-generated set.

    Args:
        count: Number of validators to get
        start_index: Starting validator index

    Returns:
        List of validator keys

    Raises:
        ValueError: If requesting more keys than available
    """
    keys = get_pregenerated_keys()

    if start_index + count > len(keys):
        raise ValueError(
            f"Requested {count} keys starting at {start_index}, "
            f"but only {len(keys)} pre-generated keys available"
        )

    result = []
    for i in range(count):
        key_data = keys[start_index + i]
        # Parse the keystore from JSON string if needed
        keystore = key_data["keystore"]
        if isinstance(keystore, str):
            keystore = json.loads(keystore)

        result.append(
            ValidatorKey(
                index=start_index + i,
                pubkey=key_data["pub"],
                privkey=key_data["priv"],
                keystore=keystore,
            )
        )

    return result


def write_validator_files(output_dir: Path, keys: list[ValidatorKey]) -> None:
    """Write validator keystores and secrets to disk for Lighthouse.

    Args:
        output_dir: Directory to write validator files
        keys: List of validator keys to write
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    keystores_dir = output_dir / "keystores"
    secrets_dir = output_dir / "secrets"
    keystores_dir.mkdir(exist_ok=True)
    secrets_dir.mkdir(exist_ok=True)

    for key in keys:
        # Write keystore
        keystore_dir = keystores_dir / f"validator_{key.index}"
        keystore_dir.mkdir(exist_ok=True)
        keystore_file = keystore_dir / "voting-keystore.json"
        with open(keystore_file, "w") as f:
            json.dump(key.keystore, f, indent=2)

        # Write secret (password)
        secret_file = secrets_dir / f"validator_{key.index}"
        with open(secret_file, "w") as f:
            f.write(DEFAULT_SECRET)

    # Write validator definitions for Lighthouse
    # Container paths: validators dir is mounted at /data/validators
    validator_definitions = []
    for key in keys:
        validator_definitions.append(
            {
                "enabled": True,
                "voting_public_key": f"0x{key.pubkey}",
                "type": "local_keystore",
                "voting_keystore_path": f"/data/validators/keystores/validator_{key.index}/voting-keystore.json",
                "voting_keystore_password_path": f"/data/validators/secrets/validator_{key.index}",
            }
        )

    import yaml
    with open(output_dir / "validator_definitions.yml", "w") as f:
        yaml.dump(validator_definitions, f)
