# MEV Playground

A minimal MEV integration testing environment for Ethereum. Spin up a complete local MEV stack with relay, builder, and all supporting infrastructure in a single command.

## Features

- **Complete MEV Stack**: Relay, builder (rbuilder), MEV-Boost, all pre-configured
- **Full Ethereum Node**: Reth (execution) + Lighthouse (consensus) with 100 validators
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
| `contender start` | Start Contender transaction spammer |
| `contender stop` | Stop Contender |

### Start Options

```bash
mev-playground start \
  --builder rbuilder|custom|none \  # Builder type (default: rbuilder)
  --builder-image IMAGE \           # Custom builder Docker image
  --relay-image IMAGE \             # Override relay image
  --data-dir PATH \                 # Custom data directory
  --no-contender \                  # Skip starting transaction spammer
  --tps 20                          # Contender transactions per second
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MEV Playground                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────────┐    ┌──────────┐                 │
│  │  Reth   │◄──►│ Lighthouse  │◄──►│MEV-Boost │                 │
│  │  (EL)   │    │  BN + VC    │    │          │                 │
│  └────┬────┘    └─────────────┘    └────┬─────┘                 │
│       │                                 │                       │
│       │ IPC                             │                       │
│       ▼                                 ▼                       │
│  ┌─────────┐                       ┌─────────┐                  │
│  │rbuilder │──────────────────────►│  Relay  │                  │
│  │(builder)│    submits blocks     │         │                  │
│  └─────────┘                       └─────────┘                  │
│                                                                 │
│                                                                 │
│  ┌─────────┐    ┌───────────┐                                   │
│  │  Dora   │    │ Contender │                                   │
│  │(explorer)    │ (spammer) │                                   │
│  └─────────┘    └───────────┘                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
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
| Dora Explorer | 8080 | http://localhost:8080 |

## Components

### Core Ethereum Stack
- **Reth** (`ghcr.io/paradigmxyz/reth:v1.8.2`) - Execution client
- **Lighthouse** (`sigp/lighthouse:v8.0.0-rc.2`) - Consensus client (beacon node + validator client)
- **100 Validators** - Pre-generated keys from fixtures

### MEV Stack
- **Relay** - Ultrasound/Turbo relay for block auction
- **rbuilder** - Flashbots block builder
- **MEV-Boost** - Validator sidecar for external block building

### Infrastructure
- **PostgreSQL** (3 instances) - Relay databases
- **Redis** - Relay cache
- **Dora** - Block explorer
- **Contender** - Transaction load generator

## Python API

```python
from mev_playground import Playground

# Create and start
playground = Playground(
    builder="rbuilder",
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
| Genesis delay | 30s |
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
- **172.28.3.x** - Builder (rbuilder)
- **172.28.4.x** - Tools (Dora, Contender)

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
