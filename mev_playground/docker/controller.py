"""Docker controller for managing containers."""

from typing import Optional
import docker
from docker.models.containers import Container
from docker.types import Mount

from mev_playground.config import DOCKER_NETWORK_NAME


class DockerController:
    """Manages Docker containers for the playground."""

    def __init__(self):
        self.client = docker.from_env()
        self._containers: dict[str, Container] = {}

    def pull_image(self, image: str) -> None:
        """Pull a Docker image if not present locally."""
        try:
            self.client.images.get(image)
        except docker.errors.ImageNotFound:
            self.client.images.pull(image)

    def pull_images_parallel(self, images: list[str]) -> None:
        """Pull multiple images in parallel."""
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.pull_image, img): img for img in images}
            for future in concurrent.futures.as_completed(futures):
                img = futures[future]
                try:
                    future.result()
                except Exception as e:
                    raise RuntimeError(f"Failed to pull image {img}: {e}")

    def run_container(
        self,
        name: str,
        image: str,
        static_ip: str,
        command: Optional[list[str]] = None,
        environment: Optional[dict[str, str]] = None,
        ports: Optional[dict[str, int]] = None,
        volumes: Optional[dict[str, dict]] = None,
        mounts: Optional[list[Mount]] = None,
        healthcheck: Optional[dict] = None,
        depends_on: Optional[list[str]] = None,
        user: Optional[str] = None,
    ) -> Container:
        """Run a container with static IP assignment.

        Args:
            name: Container name
            image: Docker image
            static_ip: Static IP address within the playground network
            command: Command to run
            environment: Environment variables
            ports: Port mappings (container_port: host_port)
            volumes: Volume mappings
            mounts: Mount configurations
            healthcheck: Docker healthcheck configuration
            depends_on: List of container names this container depends on
            user: User to run as
        """
        # Wait for dependencies to be healthy
        if depends_on:
            for dep_name in depends_on:
                if dep_name in self._containers:
                    self._wait_for_healthy(dep_name)

        # Configure networking
        networking_config = {
            DOCKER_NETWORK_NAME: self.client.api.create_endpoint_config(
                ipv4_address=static_ip
            )
        }

        # Configure port bindings
        port_bindings = None
        if ports:
            port_bindings = {f"{cp}/tcp": hp for cp, hp in ports.items()}

        container = self.client.containers.run(
            image=image,
            name=name,
            command=command,
            environment=environment,
            ports=port_bindings,
            volumes=volumes,
            mounts=mounts,
            network=DOCKER_NETWORK_NAME,
            networking_config=networking_config,
            healthcheck=healthcheck,
            detach=True,
            remove=False,
            user=user,
        )

        self._containers[name] = container
        return container

    def _wait_for_healthy(self, name: str, timeout: int = 120) -> None:
        """Wait for a container to become healthy."""
        import time

        container = self._containers.get(name)
        if not container:
            return

        start = time.time()
        while time.time() - start < timeout:
            container.reload()
            health = container.attrs.get("State", {}).get("Health", {})
            status = health.get("Status", "none")

            if status == "healthy":
                return
            elif status == "unhealthy":
                raise RuntimeError(f"Container {name} is unhealthy")

            # If no healthcheck, just check if running
            if not health and container.status == "running":
                return

            time.sleep(1)

        raise TimeoutError(f"Container {name} did not become healthy within {timeout}s")

    def wait_for_all_healthy(self, timeout: int = 120) -> None:
        """Wait for all containers to become healthy."""
        for name in self._containers:
            self._wait_for_healthy(name, timeout)

    def stop_container(self, name: str, timeout: int = 10) -> None:
        """Stop a specific container."""
        # First check our tracked containers
        if name in self._containers:
            try:
                self._containers[name].stop(timeout=timeout)
            except docker.errors.NotFound:
                pass
        else:
            # Also try to stop by name in case it exists but we're not tracking it
            try:
                container = self.client.containers.get(name)
                container.stop(timeout=timeout)
            except docker.errors.NotFound:
                pass

    def remove_container(self, name: str, force: bool = False) -> None:
        """Remove a specific container."""
        # First check our tracked containers
        if name in self._containers:
            try:
                self._containers[name].remove(force=force)
            except docker.errors.NotFound:
                pass
            del self._containers[name]
        else:
            # Also try to remove by name in case it exists but we're not tracking it
            try:
                container = self.client.containers.get(name)
                container.remove(force=force)
            except docker.errors.NotFound:
                pass

    def stop_all(self, timeout: int = 10) -> None:
        """Stop all playground containers (both tracked and untracked)."""
        # Stop tracked containers
        for name in list(self._containers.keys()):
            self.stop_container(name, timeout)

        # Also stop any containers on the playground network that we're not tracking
        try:
            network = self.client.networks.get(DOCKER_NETWORK_NAME)
            network.reload()
            for container in network.containers:
                try:
                    container.stop(timeout=timeout)
                except docker.errors.APIError:
                    pass
        except docker.errors.NotFound:
            pass

    def remove_all(self, force: bool = False) -> None:
        """Remove all playground containers (both tracked and untracked)."""
        # Remove tracked containers
        for name in list(self._containers.keys()):
            self.remove_container(name, force)

        # Also remove any containers on the playground network that we're not tracking
        try:
            network = self.client.networks.get(DOCKER_NETWORK_NAME)
            network.reload()
            for container in network.containers:
                try:
                    container.remove(force=force)
                except docker.errors.APIError:
                    pass
        except docker.errors.NotFound:
            pass

    def cleanup_existing(self, names: list[str]) -> None:
        """Remove any existing containers with the given names."""
        for name in names:
            try:
                container = self.client.containers.get(name)
                container.stop(timeout=5)
                container.remove(force=True)
            except docker.errors.NotFound:
                pass
            except docker.errors.APIError:
                # Container might already be stopped
                try:
                    container = self.client.containers.get(name)
                    container.remove(force=True)
                except docker.errors.NotFound:
                    pass

    def get_container(self, name: str) -> Optional[Container]:
        """Get a container by name."""
        return self._containers.get(name)

    def get_container_logs(self, name: str, tail: int = 100) -> str:
        """Get logs from a container."""
        container = self._containers.get(name)
        if container:
            return container.logs(tail=tail).decode("utf-8")
        return ""

    def list_containers(self) -> list[str]:
        """List all managed container names."""
        return list(self._containers.keys())
