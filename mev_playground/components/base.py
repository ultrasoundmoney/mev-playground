"""Base service definition for playground components."""

from dataclasses import dataclass, field
from typing import Optional

from docker.models.containers import Container
from docker.types import Mount

from mev_playground.docker.controller import DockerController


@dataclass
class Service:
    """A Docker service configuration with lifecycle methods."""

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

    _container: Optional[Container] = field(default=None, init=False, repr=False)

    def start(self, controller: DockerController) -> Container:
        """Start this service's container."""
        self._container = controller.run_container(
            name=self.name,
            image=self.image,
            static_ip=self.static_ip,
            command=self.command or None,
            environment=self.environment or None,
            ports=self.ports or None,
            volumes=self.volumes or None,
            mounts=self.mounts or None,
            healthcheck=self.healthcheck,
            depends_on=self.depends_on or None,
            user=self.user,
            ipc_mode=self.ipc_mode,
            pid_mode=self.pid_mode,
            shm_size=self.shm_size,
        )
        return self._container

    def stop(self, controller: DockerController) -> None:
        """Stop this service's container."""
        controller.stop_container(self.name)

    def remove(self, controller: DockerController) -> None:
        """Remove this service's container."""
        controller.remove_container(self.name)

    @property
    def container(self) -> Optional[Container]:
        """Get the container instance."""
        return self._container
