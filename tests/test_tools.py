"""Tests for Spraay gateway tool functions with mocked HTTP responses."""

from __future__ import annotations

import pytest
import httpx
import respx

from crypto_payroll_agent.tools import (
    estimate_batch,
    execute_batch,
    get_token_info,
    check_transaction,
)
from crypto_payroll_agent.config import GATEWAY_BASE_URL


MOCK_TOKEN_RESPONSE = {
    "description": "Spraay supports any ERC-20 token and native ETH on Base",
    "contract": "0x1646452F98E36A3c9Cfc3eDD8868221E207B5eEC",
    "fee": "0.3%",
    "feeBps": 30,
    "maxRecipients": 200,
    "popularTokens": {
        "USDC": {
            "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "decimals": 6,
        },
        "ETH": {"native": True, "decimals": 18},
    },
    "chains": {
        "base": {
            "chainId": 8453,
            "contract": "0x1646452F98E36A3c9Cfc3eDD8868221E207B5eEC",
            "status": "live",
        },
    },
}

MOCK_ESTIMATE_RESPONSE = {
    "estimatedGas": "45000",
    "protocolFee": "3000",
    "totalCost": "0.0023",
}

MOCK_EXECUTE_RESPONSE = {
    "to": "0x1646452F98E36A3c9Cfc3eDD8868221E207B5eEC",
    "data": "0xabcdef...",
    "value": "0",
    "chainId": 8453,
    "gasLimit": "60000",
}

MOCK_TX_STATUS = {
    "status": "confirmed",
    "blockNumber": 12345678,
    "gasUsed": "42000",
}


@respx.mock
@pytest.mark.asyncio
async def test_get_token_info():
    respx.get(f"{GATEWAY_BASE_URL}/api/v1/tokens").mock(
        return_value=httpx.Response(200, json=MOCK_TOKEN_RESPONSE)
    )

    # get_token_info is decorated with @tool — call the underlying function
    result = await get_token_info.__wrapped__()
    assert result["feeBps"] == 30
    assert "USDC" in result["popularTokens"]
    assert result["popularTokens"]["USDC"]["decimals"] == 6


@respx.mock
@pytest.mark.asyncio
async def test_estimate_batch():
    respx.post(f"{GATEWAY_BASE_URL}/api/v1/batch/estimate").mock(
        return_value=httpx.Response(200, json=MOCK_ESTIMATE_RESPONSE)
    )

    result = await estimate_batch.__wrapped__(
        token="USDC",
        recipients=["0x" + "a1" * 20, "0x" + "b2" * 20],
        amounts=["1000000", "2000000"],
    )
    assert "estimatedGas" in result
    assert "protocolFee" in result


@respx.mock
@pytest.mark.asyncio
async def test_execute_batch():
    respx.post(f"{GATEWAY_BASE_URL}/api/v1/batch/execute").mock(
        return_value=httpx.Response(200, json=MOCK_EXECUTE_RESPONSE)
    )

    result = await execute_batch.__wrapped__(
        token="USDC",
        recipients=["0x" + "a1" * 20],
        amounts=["1000000"],
        sender="0x" + "cc" * 20,
    )
    assert result["chainId"] == 8453
    assert "to" in result
    assert "data" in result


@respx.mock
@pytest.mark.asyncio
async def test_check_transaction_found():
    tx_hash = "0x" + "dd" * 32
    respx.get(f"{GATEWAY_BASE_URL}/api/v1/tx/{tx_hash}").mock(
        return_value=httpx.Response(200, json=MOCK_TX_STATUS)
    )

    result = await check_transaction.__wrapped__(tx_hash=tx_hash)
    assert result["status"] == "confirmed"
    assert "explorer_url" in result
    assert "basescan.org" in result["explorer_url"]


@respx.mock
@pytest.mark.asyncio
async def test_check_transaction_not_found():
    tx_hash = "0x" + "ee" * 32
    respx.get(f"{GATEWAY_BASE_URL}/api/v1/tx/{tx_hash}").mock(
        return_value=httpx.Response(404)
    )

    result = await check_transaction.__wrapped__(tx_hash=tx_hash)
    assert result["status"] == "not_found"
    assert tx_hash in result["explorer_url"]


@respx.mock
@pytest.mark.asyncio
async def test_estimate_batch_unichain():
    respx.post(f"{GATEWAY_BASE_URL}/api/v1/batch/estimate").mock(
        return_value=httpx.Response(200, json=MOCK_ESTIMATE_RESPONSE)
    )

    result = await estimate_batch.__wrapped__(
        token="USDC",
        recipients=["0x" + "a1" * 20],
        amounts=["1000000"],
        chain="unichain",
    )
    assert "estimatedGas" in result
