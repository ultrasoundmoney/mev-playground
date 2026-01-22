"""PostgreSQL component for relay databases."""

from pathlib import Path
from docker.types import Mount

from mev_playground.components.base import Component, ContainerConfig
from mev_playground.config import StaticIPs, StaticPorts


class PostgresComponent(Component):
    """PostgreSQL database for the relay."""

    def __init__(
        self,
        data_dir: Path,
        instance_name: str,
        static_ip: str,
    ):
        """Initialize PostgreSQL component.

        Args:
            data_dir: Base data directory
            instance_name: Name for this instance (mevdb, localdb, globaldb)
            static_ip: Static IP for this instance
        """
        super().__init__(data_dir)
        self._instance_name = instance_name
        self._static_ip = static_ip
        self._data_path = data_dir / "data" / "postgres" / instance_name

    @property
    def name(self) -> str:
        return self._instance_name

    def get_container_config(self) -> ContainerConfig:
        self._data_path.mkdir(parents=True, exist_ok=True)

        return ContainerConfig(
            name=self.name,
            image="postgres:15-alpine",
            static_ip=self._static_ip,
            environment={
                "POSTGRES_USER": "postgres",
                "POSTGRES_PASSWORD": "postgres",
                "POSTGRES_DB": "postgres",
            },
            # No host port binding - only accessible within Docker network via static IP
            ports={},
            mounts=[
                Mount(
                    target="/var/lib/postgresql/data",
                    source=str(self._data_path),
                    type="bind",
                ),
            ],
            healthcheck={
                "test": ["CMD-SHELL", "pg_isready -U postgres"],
                "interval": 3000000000,
                "timeout": 2000000000,
                "retries": 10,
                "start_period": 5000000000,
            },
            # Postgres image entrypoint handles user switching internally via gosu
            user="root",
        )

    @property
    def url(self) -> str:
        return f"postgres://postgres:postgres@{self._static_ip}:{StaticPorts.POSTGRES}/postgres?sslmode=disable"


def create_relay_databases(data_dir: Path) -> tuple[PostgresComponent, PostgresComponent, PostgresComponent]:
    """Create all three PostgreSQL instances needed for the relay.

    Returns:
        Tuple of (mevdb, localdb, globaldb) components
    """
    mevdb = PostgresComponent(data_dir, "mevdb", StaticIPs.MEVDB)
    localdb = PostgresComponent(data_dir, "localdb", StaticIPs.LOCALDB)
    globaldb = PostgresComponent(data_dir, "globaldb", StaticIPs.GLOBALDB)

    return mevdb, localdb, globaldb
