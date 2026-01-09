"""JWT secret generation for EL-CL communication."""

import secrets
from pathlib import Path


def generate_jwt_secret(output_path: Path) -> str:
    """Generate a JWT secret for EL-CL authentication.

    Args:
        output_path: Path to write the JWT secret file

    Returns:
        The generated JWT secret as a hex string
    """
    # Generate 32 random bytes
    jwt_secret = secrets.token_hex(32)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to file (without 0x prefix, as expected by clients)
    output_path.write_text(jwt_secret)

    return jwt_secret
