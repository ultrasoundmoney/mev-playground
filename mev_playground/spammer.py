"""Transaction spammer for testing rbuilder integration."""

import time
from eth_account import Account
from eth_account.signers.local import LocalAccount
import requests
from rich.console import Console

console = Console()

# Foundry/Anvil test accounts (pre-funded in genesis with ~4.7M ETH each)
# These are well-known test keys - DO NOT use on mainnet
TEST_ACCOUNTS = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # 0xf39Fd6...
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",  # 0x70997...
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",  # 0x3C44Cd...
]

CHAIN_ID = 1337  # mev_playground devnet


class TransactionSpammer:
    """Send test transactions to populate the mempool for rbuilder testing."""

    def __init__(self, rpc_url: str = "http://localhost:8545"):
        self.rpc_url = rpc_url
        self.accounts: list[LocalAccount] = [
            Account.from_key(pk) for pk in TEST_ACCOUNTS
        ]
        self.nonces: dict[str, int] = {}

    def _rpc_call(self, method: str, params: list) -> dict:
        """Make JSON-RPC call to Reth."""
        response = requests.post(
            self.rpc_url,
            json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
        )
        return response.json()

    def get_nonce(self, address: str) -> int:
        """Get current nonce for address."""
        if address not in self.nonces:
            result = self._rpc_call("eth_getTransactionCount", [address, "pending"])
            self.nonces[address] = int(result["result"], 16)
        return self.nonces[address]

    def get_gas_price(self) -> int:
        """Get current gas price."""
        result = self._rpc_call("eth_gasPrice", [])
        return int(result["result"], 16)

    def send_transaction(
        self, from_account: LocalAccount, to_address: str, value_wei: int
    ) -> str:
        """Sign and send a transaction."""
        nonce = self.get_nonce(from_account.address)
        gas_price = self.get_gas_price()

        tx = {
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": 21000,
            "to": to_address,
            "value": value_wei,
            "chainId": CHAIN_ID,
        }

        signed = from_account.sign_transaction(tx)
        result = self._rpc_call(
            "eth_sendRawTransaction", [signed.raw_transaction.hex()]
        )

        if "error" in result:
            raise Exception(f"TX failed: {result['error']}")

        self.nonces[from_account.address] = nonce + 1
        return result["result"]

    def spam(
        self,
        tx_per_slot: int = 5,
        duration_slots: int | None = None,
        slot_time: int = 12,
    ):
        """Send transactions at specified rate.

        Args:
            tx_per_slot: Number of transactions to send per slot
            duration_slots: Number of slots to spam (None = infinite until Ctrl+C)
            slot_time: Seconds per slot (default: 12)
        """
        if duration_slots is None:
            console.print(
                f"[bold]Starting spammer:[/bold] {tx_per_slot} tx/slot (Ctrl+C to stop)"
            )
        else:
            console.print(
                f"[bold]Starting spammer:[/bold] {tx_per_slot} tx/slot for {duration_slots} slots"
            )
        console.print(
            f"[dim]Using accounts: {[a.address[:10]+'...' for a in self.accounts]}[/dim]"
        )

        total_tx = 0
        slot = 0
        try:
            while duration_slots is None or slot < duration_slots:
                slot_start = time.time()

                for i in range(tx_per_slot):
                    sender = self.accounts[i % len(self.accounts)]
                    receiver = self.accounts[(i + 1) % len(self.accounts)]

                    try:
                        tx_hash = self.send_transaction(
                            sender, receiver.address, 10**15  # 0.001 ETH
                        )
                        total_tx += 1
                        console.print(
                            f"  Slot {slot}: TX {tx_hash[:10]}... from {sender.address[:10]}..."
                        )
                    except Exception as e:
                        console.print(f"  [red]Error: {e}[/red]")

                # Wait for remainder of slot
                elapsed = time.time() - slot_start
                if elapsed < slot_time:
                    time.sleep(slot_time - elapsed)

                slot += 1
        except KeyboardInterrupt:
            console.print("")  # New line after ^C

        console.print(f"[green]Done! Sent {total_tx} transactions[/green]")
