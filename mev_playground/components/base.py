"""Base service definition for playground components."""

from typing import Optional

from docker.models.containers import Container
from docker.types import Mount

from mev_playground.docker.controller import DockerController


class Service:
    """A Docker service configuration with lifecycle methods.

    Uses a builder pattern for configuration:
        Service("reth")
            .with_image("ghcr.io/paradigmxyz/reth:latest")
            .with_static_ip("10.0.0.2")
            .with_command("node", "--chain", "/genesis/genesis.json")
            .with_port(8545, 8545)
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.image: str = ""
        self.static_ip: str = ""
        self.command: list[str] = []
        self.environment: dict[str, str] = {}
        self.ports: dict[int, int] = {}
        self.volumes: dict[str, dict] = {}
        self.mounts: list[Mount] = []
        self.healthcheck: Optional[dict] = None
        self.depends_on: list[str] = []
        self.user: Optional[str] = None
        self.ipc_mode: Optional[str] = None
        self.pid_mode: Optional[str] = None
        self.shm_size: Optional[str] = None
        self._container: Optional[Container] = None

    def __repr__(self) -> str:
        return f"Service(name={self.name!r}, image={self.image!r})"

    # --- Builder methods ---

    def with_image(self, image: str) -> "Service":
        self.image = image
        return self

    def with_static_ip(self, static_ip: str) -> "Service":
        self.static_ip = static_ip
        return self

    def with_command(self, *args: str) -> "Service":
        self.command = list(args)
        return self

    def with_env(self, env: dict[str, str] | None = None, **kwargs: str) -> "Service":
        if env:
            self.environment.update(env)
        self.environment.update(kwargs)
        return self

    def with_port(self, container_port: int, host_port: int) -> "Service":
        self.ports[container_port] = host_port
        return self

    def with_volume(self, name: str, config: dict) -> "Service":
        self.volumes[name] = config
        return self

    def with_mount(
        self,
        target: str,
        source: str,
        type: str = "bind",
        read_only: bool = False,
    ) -> "Service":
        self.mounts.append(Mount(target=target, source=source, type=type, read_only=read_only))
        return self

    def with_healthcheck(
        self,
        test: list[str],
        interval: int,
        timeout: int,
        retries: int,
        start_period: int,
    ) -> "Service":
        self.healthcheck = {
            "test": test,
            "interval": interval,
            "timeout": timeout,
            "retries": retries,
            "start_period": start_period,
        }
        return self

    def with_depends_on(self, *names: str) -> "Service":
        self.depends_on = list(names)
        return self

    def with_user(self, user: str) -> "Service":
        self.user = user
        return self

    def with_ipc_mode(self, ipc_mode: str) -> "Service":
        self.ipc_mode = ipc_mode
        return self

    def with_pid_mode(self, pid_mode: str) -> "Service":
        self.pid_mode = pid_mode
        return self

    def with_shm_size(self, shm_size: str) -> "Service":
        self.shm_size = shm_size
        return self

    # --- Lifecycle methods ---

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
