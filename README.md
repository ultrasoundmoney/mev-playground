# MEV Playground

A minimal MEV integration testing environment for Ethereum. Spin up a complete local MEV stack with relay, builder, and all supporting infrastructure in a single command.

## Features

- **Complete MEV Stack**: Relay, builder (rbuilder), MEV-Boost, all pre-configured
- **Block Merging**: Test block merging with one or two builders submitting to the relay
- **Full Ethereum Node**: reth-simulator (execution with block merging extensions) + Lighthouse (consensus) with 100 validators
- **Zero Configuration**: Pre-generated genesis, validator keys, and JWT secrets
- **Transaction Spamming**: Built-in tools to populate the mempool for testing
- **Block Explorer**: Dora explorer included for inspecting blocks
- **Docker-Based**: Everything runs in containers with automatic networking

## Requirements

- Python 3.10+
- Docker

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/ultrasoundmoney/mev-playground.git

# Or with pipx (recommended for CLI tools)
pipx install git+https://github.com/ultrasoundmoney/mev-playground.git
```

## Quick Start

```bash
# Start the playground
mev-playground start

# Start with two builders for block merging
mev-playground start --with-builder2

# Check status
mev-playground status

# View logs from a component
mev-playground logs reth

# Stop (preserves data)
mev-playground stop

# Delete everything and start fresh
mev-playground nuke
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `start` | Start the MEV playground |
| `stop` | Stop containers (preserve data) |
| `nuke` | Delete all data and containers |
| `status` | Show component health status |
| `logs <component>` | View logs from a component |
| `info` | Show configuration and endpoints |
| `spam` | Run simple Python transaction spammer |
| `assert-blocks` | Assert blocks have expected extraData for n slots |
| `contender start` | Start Contender transaction spammer |
| `contender stop` | Stop Contender |

### Start Options

```bash
mev-playground start \
  --execution-image IMAGE \         # Override execution client image (default: reth-simulator:latest)
  --builder rbuilder|custom|none \  # Builder type (default: rbuilder)
  --builder-image IMAGE \           # Custom builder Docker image
  --relay-image IMAGE \             # Override relay image
  --data-dir PATH \                 # Custom data directory
  --with-builder2 \                 # Start a second builder for block merging
  --no-contender \                  # Skip starting transaction spammer
  --tps 20                          # Contender transactions per second
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           MEV Playground                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────┐                     │
│  │reth-simulator│◄──►│ Lighthouse  │◄──►│MEV-Boost │                     │
│  │     (EL)     │    │  BN + VC    │    │          │                     │
│  └──────┬───────┘    └─────────────┘    └────┬─────┘                     │
│         │                                    │                           │
│         │ IPC                                │                           │
│         ▼                                    ▼                           │
│  ┌──────────┐    submits blocks      ┌───────────┐                       │
│  │ rbuilder │───────────────────────►│   Relay   │                       │
│  │(builder 1)│                       │           │                       │
│  └──────────┘                        │  (merges  │                       │
│  ┌──────────┐    submits blocks      │  blocks)  │                       │
│  │ rbuilder2│───────────────────────►│           │                       │
│  │(builder 2)│  (optional)           └───────────┘                       │
│  └──────────┘                                                            │
│         ▲                                                                │
│         │                                                                │
│  ┌────────────┐    ┌────────────┐                                        │
│  │ RPC Proxy 1│    │ RPC Proxy 2│  (route private txs to each builder)   │
│  └─────┬──────┘    └─────┬──────┘                                        │
│        ▲                 ▲                                                │
│        │                 │                                                │
│  ┌─────┴─────┐    ┌─────┴─────┐    ┌─────────┐                           │
│  │ Contender │    │Contender 2│    │  Dora   │                           │
│  │ (spammer) │    │ (spammer) │    │(explorer)│                          │
│  └───────────┘    └───────────┘    └─────────┘                           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Endpoints

| Service | Port | URL |
|---------|------|-----|
| Reth HTTP RPC | 8545 | http://localhost:8545 |
| Reth WebSocket | 8546 | ws://localhost:8546 |
| Lighthouse Beacon | 3500 | http://localhost:3500 |
| MEV-Boost | 18550 | http://localhost:18550 |
| Relay | 80 | http://localhost:80 |
| rbuilder RPC | 8645 | http://localhost:8645 |
| rbuilder2 RPC | 8646 | http://localhost:8646 |
| RPC Proxy 1 | 8650 | http://localhost:8650 |
| Dora Explorer | 8080 | http://localhost:8080 |

## Components

### Core Ethereum Stack
- **reth-simulator** (`reth-simulator:latest`) - Execution client with block merging extensions
- **Lighthouse** (`sigp/lighthouse:v8.0.0-rc.2`) - Consensus client (beacon node + validator client)
- **100 Validators** - Pre-generated keys from fixtures

### MEV Stack
- **Relay** - Ultrasound/Turbo relay for block auction (with block merging support)
- **rbuilder** - Flashbots block builder (1 or 2 instances)
- **MEV-Boost** - Validator sidecar for external block building
- **RPC Proxy** - Routes private transactions (`eth_sendBundle`, `eth_sendRawTransaction`) to the builder, other RPC calls to Reth

### Infrastructure
- **PostgreSQL** (3 instances) - Relay databases
- **Redis** - Relay cache
- **Dora** - Block explorer
- **Contender** - Transaction load generator

## Block Merging

Block merging allows the relay to combine blocks from multiple builders into a single optimal block. The playground supports testing this with one or two builders.

### Single Builder (default)

```bash
mev-playground start
```

One builder (`rbuilder`) submits blocks to the relay. The execution client (`reth-simulator`) runs with block merging extensions enabled, including a builder collateral map and relay fee recipient configuration.

### Two Builders

```bash
mev-playground start --with-builder2
```

Two builders with different coinbase keys each submit blocks to the relay, which merges them. Each builder gets its own:

- **RPC Proxy** - Routes private transaction flow (`eth_sendBundle`, `eth_sendRawTransaction`) to the assigned builder, while forwarding all other RPC calls to Reth
- **Contender instance** - Sends bundles through the proxy so each builder receives unique private order flow

This setup simulates the production block merging scenario where the relay merges blocks from competing builders.

## Python API

```python
from mev_playground import Playground

# Single builder (default)
playground = Playground(
    builder="rbuilder",
    with_contender=True,
    contender_tps=20,
)
playground.start()

# Two builders for block merging
playground = Playground(
    builder="rbuilder",
    with_builder2=True,
    with_contender=True,
    contender_tps=20,
)
playground.start()

# Check status
status = playground.status()
for name, info in status.items():
    print(f"{name}: {info['health']}")

# View logs
logs = playground.logs("reth", tail=50)

# Cleanup
playground.stop()      # Stop containers, keep data
playground.nuke()      # Delete everything
```

## Configuration

Default data directory: `~/.mev_playground`

| Setting | Default |
|---------|---------|
| Chain ID | 3151908 |
| Seconds per slot | 12 |
| Validator count | 100 |
| Genesis delay | 0 |
| Fork | Electra (enabled at genesis) |

### Genesis Generation

The playground uses the same genesis generation approach as [Kurtosis ethereum-package](https://github.com/ethpandaops/ethereum-package):

- **EL + CL genesis** generated dynamically using `ethpandaops/ethereum-genesis-generator`
- **Validator keystores** generated using `eth2-val-tools` from the same mnemonic
- **Coordinated genesis** - both layers use the same genesis timestamp and validators root

This ensures fresh genesis data on each start, avoiding stale genesis issues.

## Network

All containers run on a custom Docker bridge network (`mev-playground`) with static IP assignment:

- **172.28.1.x** - Core Ethereum (Reth, Lighthouse, MEV-Boost)
- **172.28.2.x** - Relay infrastructure (Relay, Redis, Postgres)
- **172.28.3.x** - Builders (rbuilder, rbuilder2)
- **172.28.4.x** - Tools (Dora, Contender)
- **172.28.5.x** - RPC Proxies

## Development

```bash
# Clone the repo
git clone https://github.com/ultrasoundmoney/mev-playground.git
cd mev-playground

# Install in development mode
pip install -e .

# Run the CLI
mev-playground start
```
