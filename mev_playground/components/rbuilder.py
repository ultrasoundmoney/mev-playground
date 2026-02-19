"""rbuilder block builder service."""

from pathlib import Path
from textwrap import dedent

from mev_playground.service import Service
from mev_playground.config import (
    StaticIPs,
    StaticPorts,
    DEFAULT_MEV_SECRET_KEY,
)


def _generate_rbuilder_config(coinbase_secret_key: str) -> str:
    """Generate rbuilder TOML configuration."""
    # Strip 0x prefix from keys if present (rbuilder expects raw hex)
    coinbase_key = coinbase_secret_key
    if coinbase_key.startswith("0x"):
        coinbase_key = coinbase_key[2:]
    relay_key = DEFAULT_MEV_SECRET_KEY
    if relay_key.startswith("0x"):
        relay_key = relay_key[2:]

    # Note: [[relays]] table array must come AFTER all scalar values in TOML
    return dedent(f"""\
        chain = "/genesis/genesis.json"
        reth_datadir = "/reth_data"
        el_node_ipc_path = "/reth_data/reth.ipc"
        cl_node_url = ["http://{StaticIPs.LIGHTHOUSE_BN}:{StaticPorts.LIGHTHOUSE_HTTP}"]
        enabled_relays = ["ultrasound-local"]
        coinbase_secret_key = "{coinbase_key}"
        relay_secret_key = "{relay_key}"
        live_builders = ["fast-ordering"]
        jsonrpc_server_port = {StaticPorts.RBUILDER_RPC}
        jsonrpc_server_ip = "0.0.0.0"
        log_level = "info,rbuilder=debug"
        log_json = false
        full_telemetry_server_port = 6060
        full_telemetry_server_ip = "0.0.0.0"
        root_hash_use_sparse_trie = true
        root_hash_compare_sparse_trie = false
        extra_data = "🦇🔊"
        slot_delta_to_start_bidding_ms = -12000

        [[builders]]
        name = "fast-ordering"
        algo = "ordering-builder"
        discard_txs = true
        sorting = "mev-gas-price"
        failed_order_retries = 1
        drop_failed_orders = true
        build_duration_deadline_ms = 3000

        [[relays]]
        name = "ultrasound-local"
        url = "http://{StaticIPs.RELAY}:{StaticPorts.RELAY_HTTP}"
        use_ssz_for_submit = true
        use_gzip_for_submit = false
        priority = 0
    """)


def rbuilder_service(
    data_dir: Path,
    image: str,
    reth_data_path: Path,
    coinbase_secret_key: str = "0x" + "01" * 32,
) -> Service:
    """Create an rbuilder block builder service."""
    config_path = data_dir / "config" / "rbuilder.toml"
    artifacts_path = data_dir / "artifacts"

    # Write config file
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(_generate_rbuilder_config(coinbase_secret_key))

    return (
        Service("rbuilder")
        .with_image(image)
        .with_static_ip(StaticIPs.RBUILDER)
        .with_command("run", "/config/rbuilder.toml")
        .with_env(
            COINBASE_SECRET_KEY=coinbase_secret_key,
            RELAY_SECRET_KEY=DEFAULT_MEV_SECRET_KEY,
        )
        .with_port(StaticPorts.RBUILDER_RPC, StaticPorts.RBUILDER_RPC)
        .with_port(6060, 6060)
        .with_mount("/config", str(config_path.parent.resolve()), read_only=True)
        .with_mount("/reth_data", str(reth_data_path.resolve()))
        .with_mount("/genesis", str(artifacts_path.resolve()), read_only=True)
        .with_healthcheck(
            test=["NONE"],
            interval=10000000000,
            timeout=5000000000,
            retries=10,
            start_period=60000000000,
        )
        .with_depends_on("reth", "mev-ultrasound-relay", "lighthouse-bn")
        .with_pid_mode("container:reth")
    )
