"""Abstract base class for playground components."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from docker.models.containers import Container
from docker.types import Mount

from mev_playground.docker.controller import DockerController


@dataclass
class ContainerConfig:
    """Configuration for a Docker container."""

    name: str
    image: str
    static_ip: str
    command: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    ports: dict[int, int] = field(default_factory=dict)  # container_port: host_port
    volumes: dict[str, dict] = field(default_factory=dict)
    mounts: list[Mount] = field(default_factory=list)
    healthcheck: Optional[dict] = None
    depends_on: list[str] = field(default_factory=list)
    user: Optional[str] = None
    ipc_mode: Optional[str] = None  # IPC namespace mode (e.g., "shareable", "container:<name>")
    pid_mode: Optional[str] = None  # PID namespace mode (e.g., "container:<name>")
    shm_size: Optional[str] = None  # Shared memory size (e.g., "1g", "512m")


class Component(ABC):
    """Abstract base class for all playground components."""

    def __init__(self, data_dir: Path):
        """Initialize the component.

        Args:
            data_dir: Base data directory for the playground
        """
        self.data_dir = data_dir
        self._container: Optional[Container] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the component name."""
        pass

    @abstractmethod
    def get_container_config(self) -> ContainerConfig:
        """Return the container configuration for this component."""
        pass

    def start(self, controller: DockerController) -> Container:
        """Start the component container.

        Args:
            controller: Docker controller instance

        Returns:
            The started container
        """
        config = self.get_container_config()

        self._container = controller.run_container(
            name=config.name,
            image=config.image,
            static_ip=config.static_ip,
            command=config.command if config.command else None,
            environment=config.environment if config.environment else None,
            ports=config.ports if config.ports else None,
            volumes=config.volumes if config.volumes else None,
            mounts=config.mounts if config.mounts else None,
            healthcheck=config.healthcheck,
            depends_on=config.depends_on if config.depends_on else None,
            user=config.user,
            ipc_mode=config.ipc_mode,
            pid_mode=config.pid_mode,
            shm_size=config.shm_size,
        )

        return self._container

    def stop(self, controller: DockerController) -> None:
        """Stop the component container."""
        controller.stop_container(self.name)

    def remove(self, controller: DockerController) -> None:
        """Remove the component container."""
        controller.remove_container(self.name)

    @property
    def container(self) -> Optional[Container]:
        """Get the container instance."""
        return self._container
