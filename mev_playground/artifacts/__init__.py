"""Artifact generation for MEV Playground."""

import json
from pathlib import Path

from mev_playground.artifacts.jwt import generate_jwt_secret
from mev_playground.artifacts.genesis import generate_el_genesis
from mev_playground.artifacts.keys import get_validator_keys, write_validator_files
from mev_playground.artifacts.beacon_state import generate_beacon_genesis

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def get_genesis_timestamp() -> int:
    """Get genesis timestamp from EL genesis fixture."""
    with open(FIXTURES_DIR / "el_genesis.json") as f:
        genesis = json.load(f)
    return int(genesis["timestamp"], 16)


def get_genesis_validators_root() -> str:
    """Get genesis validators root from fixture."""
    root = (FIXTURES_DIR / "genesis_validators_root.txt").read_text().strip()
    if not root.startswith("0x"):
        root = "0x" + root
    return root


__all__ = [
    "generate_jwt_secret",
    "generate_el_genesis",
    "get_validator_keys",
    "write_validator_files",
    "generate_beacon_genesis",
    "get_genesis_timestamp",
    "get_genesis_validators_root",
]
