"""Example usage of MEV Playground as a library."""

from mev_playground import Playground


def main():
    """Example: Start the playground programmatically."""
    # Create playground with default config
    playground = Playground(
        relay_image="turbo-relay-combined:latest",
        builder="rbuilder",
    )

    # Start all components
    playground.start()

    # Check status
    print("\nComponent status:")
    for name, info in playground.status().items():
        print(f"  {name}: {info['status']} ({info['health']})")

    # To stop:
    # playground.stop()

    # To nuke (delete all data):
    # playground.nuke()


if __name__ == "__main__":
    main()
