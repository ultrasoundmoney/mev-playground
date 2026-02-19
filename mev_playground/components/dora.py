"""Dora the Explorer block explorer service."""

from pathlib import Path
from textwrap import dedent

from mev_playground.service import Service
from mev_playground.config import StaticIPs, StaticPorts


DORA_PORT = 8080


def _generate_dora_config() -> str:
    """Generate Dora configuration YAML."""
    return dedent(f"""\
        logging:
          outputLevel: "info"

        chain:
          displayName: "MEV Playground Devnet"

        server:
          host: "0.0.0.0"
          port: "{DORA_PORT}"

        frontend:
          enabled: true
          siteName: "MEV Playground Explorer"
          siteSubtitle: "Local Devnet"
          ethExplorerLink: ""

        beaconapi:
          endpoints:
            - name: "lighthouse"
              url: "http://{StaticIPs.LIGHTHOUSE_BN}:{StaticPorts.LIGHTHOUSE_HTTP}"
          localCacheSize: 100

        executionapi:
          endpoints:
            - name: "reth"
              url: "http://{StaticIPs.RETH}:{StaticPorts.RETH_HTTP}"
          depositDeployBlock: 0

        indexer:
          inMemoryEpochs: 3
          activityHistoryLength: 6
          disableSynchronizer: false
          syncEpochCooldown: 1
          maxParallelValidatorSetRequests: 1

        database:
          engine: "sqlite"
          sqlite:
            file: "/data/dora.sqlite"
    """)


def dora_service(data_dir: Path) -> Service:
    """Create a Dora block explorer service."""
    config_path = data_dir / "config" / "dora"
    data_path = data_dir / "data" / "dora"
    config_path.mkdir(parents=True, exist_ok=True)
    data_path.mkdir(parents=True, exist_ok=True)

    config_file = config_path / "config.yaml"
    config_file.write_text(_generate_dora_config())

    return (
        Service("dora")
        .with_image("pk910/dora-the-explorer:latest")
        .with_static_ip(StaticIPs.DORA)
        .with_command("-config", "/config/config.yaml")
        .with_port(DORA_PORT, DORA_PORT)
        .with_mount("/config", str(config_path), read_only=True)
        .with_mount("/data", str(data_path))
        .with_healthcheck(
            test=[
                "CMD-SHELL",
                f"bash -c 'echo >/dev/tcp/localhost/{DORA_PORT}' 2>/dev/null || exit 1",
            ],
            interval=5000000000,
            timeout=3000000000,
            retries=10,
            start_period=10000000000,
        )
        .with_depends_on("lighthouse-bn", "reth")
    )
