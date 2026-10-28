"""MAF tools for interacting with the Spraay Protocol Gateway.

Each tool wraps a single gateway endpoint. The `approval_mode` on
`execute_batch` requires explicit human approval before signing,
while read-only tools run without approval.

Gateway costs (x402 protocol):
  - Estimates: $0.001 per call
  - Execution: $0.02 per call
  - Token info: free
"""

from __future__ import annotations

import httpx
from agent_framework import tool

from crypto_payroll_agent.config import GATEWAY_BASE_URL


@tool(approval_mode="never_require")
async def get_token_info() -> dict:
    """Fetch supported tokens, chains, and contract addresses from the Spraay gateway.

    Returns a dict with token details (addresses, decimals), supported chains,
    the batch contract address, max recipients per batch, and protocol fee info.
    No cost — this endpoint is free.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GATEWAY_BASE_URL}/api/v1/tokens",
            timeout=15,
        )
        response.raise_for_status()
        return response.json()


@tool(approval_mode="never_require")
async def estimate_batch(
    token: str,
    recipients: list[str],
    amounts: list[str],
    chain: str = "base",
) -> dict:
    """Estimate gas and fees for a batch payment.

    Args:
        token: Token symbol (e.g. "USDC", "ETH") or contract address.
        recipients: List of recipient wallet addresses (max 200).
        amounts: List of amounts in raw base units (e.g. "1000000" for 1 USDC).
                 Must match the length of recipients.
        chain: Target chain — "base" (default) or "unichain".

    Returns a dict with estimated gas cost, protocol fee, and total cost.
    Cost: ~$0.001 per call (x402 micropayment).
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/v1/batch/estimate",
            json={
                "token": token,
                "recipients": recipients,
                "amounts": amounts,
                "chain": chain,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


@tool(approval_mode="always_require")
async def execute_batch(
    token: str,
    recipients: list[str],
    amounts: list[str],
    sender: str,
    chain: str = "base",
) -> dict:
    """Execute a batch payment through the Spraay gateway.

    Returns an unsigned transaction that the sender must sign and broadcast.
    The transaction includes the protocol fee (0.3%).

    IMPORTANT: This returns an unsigned transaction — no funds move until
    the sender signs and submits it on-chain. Human approval is always
    required before this tool runs.

    Args:
        token: Token symbol (e.g. "USDC") or contract address.
        recipients: List of recipient wallet addresses (max 200).
        amounts: List of amounts in raw base units matching recipients length.
        sender: The sender's wallet address.
        chain: Target chain — "base" (default) or "unichain".

    Returns a dict with unsigned transaction fields:
        {to, data, value, chainId, gasLimit}
    Cost: ~$0.02 per call (x402 micropayment).
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/v1/batch/execute",
            json={
                "token": token,
                "recipients": recipients,
                "amounts": amounts,
                "sender": sender,
                "chain": chain,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


@tool(approval_mode="never_require")
async def check_transaction(tx_hash: str, chain: str = "base") -> dict:
    """Check the status of a submitted transaction on-chain.

    Args:
        tx_hash: The transaction hash to look up.
        chain: The chain to check — "base" (default) or "unichain".

    Returns a dict with transaction status and details.
    """
    from crypto_payroll_agent.config import (
        BASE_EXPLORER_URL,
        UNICHAIN_EXPLORER_URL,
    )

    explorer = BASE_EXPLORER_URL if chain == "base" else UNICHAIN_EXPLORER_URL

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GATEWAY_BASE_URL}/api/v1/tx/{tx_hash}",
            params={"chain": chain},
            timeout=15,
        )
        if response.status_code == 404:
            return {
                "status": "not_found",
                "tx_hash": tx_hash,
                "explorer_url": f"{explorer}/tx/{tx_hash}",
                "message": "Transaction not found. It may still be pending.",
            }
        response.raise_for_status()
        result = response.json()
        result["explorer_url"] = f"{explorer}/tx/{tx_hash}"
        return result
