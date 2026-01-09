"""Docker network management for MEV Playground."""

import docker
from docker.types import IPAMConfig, IPAMPool

from mev_playground.config import DOCKER_NETWORK_NAME, DOCKER_NETWORK_SUBNET


class NetworkManager:
    """Manages the Docker network for the playground."""

    def __init__(self, client: docker.DockerClient):
        self.client = client
        self.network = None

    def create_network(self) -> None:
        """Create the playground network with static IP support."""
        # Check if network already exists
        try:
            self.network = self.client.networks.get(DOCKER_NETWORK_NAME)
            return
        except docker.errors.NotFound:
            pass

        # Create network with specific subnet for static IPs
        ipam_config = IPAMConfig(
            pool_configs=[IPAMPool(subnet=DOCKER_NETWORK_SUBNET)]
        )

        self.network = self.client.networks.create(
            name=DOCKER_NETWORK_NAME,
            driver="bridge",
            ipam=ipam_config,
            check_duplicate=True,
        )

    def remove_network(self) -> None:
        """Remove the playground network."""
        if self.network:
            try:
                self.network.remove()
            except docker.errors.NotFound:
                pass
            self.network = None
        else:
            # Try to remove by name if we don't have a reference
            try:
                network = self.client.networks.get(DOCKER_NETWORK_NAME)
                network.remove()
            except docker.errors.NotFound:
                pass

    def exists(self) -> bool:
        """Check if the network exists."""
        try:
            self.client.networks.get(DOCKER_NETWORK_NAME)
            return True
        except docker.errors.NotFound:
            return False
