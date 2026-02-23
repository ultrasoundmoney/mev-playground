"""PostgreSQL service for relay databases."""

from pathlib import Path

from mev_playground.service import Service
from mev_playground.config import StaticIPs


def postgres_service(data_dir: Path, instance_name: str, static_ip: str) -> Service:
    """Create a PostgreSQL database service.

    Args:
        data_dir: Base data directory
        instance_name: Name for this instance (mevdb, localdb, globaldb)
        static_ip: Static IP for this instance
    """
    data_path = data_dir / "data" / "postgres" / instance_name
    data_path.mkdir(parents=True, exist_ok=True)

    return (
        Service(instance_name)
        .with_image("postgres:15-alpine")
        .with_static_ip(static_ip)
        .with_env(
            POSTGRES_USER="postgres",
            POSTGRES_PASSWORD="postgres",
            POSTGRES_DB="postgres",
        )
        .with_mount("/var/lib/postgresql/data", str(data_path))
        .with_healthcheck(
            test=["CMD-SHELL", "pg_isready -U postgres"],
            interval=3000000000,
            timeout=2000000000,
            retries=10,
            start_period=5000000000,
        )
    )


def create_relay_databases(data_dir: Path) -> tuple[Service, Service, Service]:
    """Create all three PostgreSQL instances needed for the relay.

    Returns:
        Tuple of (mevdb, localdb, globaldb) services
    """
    mevdb = postgres_service(data_dir, "mevdb", StaticIPs.MEVDB)
    localdb = postgres_service(data_dir, "localdb", StaticIPs.LOCALDB)
    globaldb = postgres_service(data_dir, "globaldb", StaticIPs.GLOBALDB)

    return mevdb, localdb, globaldb
