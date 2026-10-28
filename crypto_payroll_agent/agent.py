"""Payroll agent wiring — connects tools, guardrails, and the LLM."""

from __future__ import annotations

from openai import AsyncOpenAI
from agent_framework import Agent

from crypto_payroll_agent.config import OPENAI_API_KEY, OPENAI_MODEL
from crypto_payroll_agent.tools import (
    estimate_batch,
    execute_batch,
    get_token_info,
    check_transaction,
)
from crypto_payroll_agent.guardrails import before_tool_check

SYSTEM_INSTRUCTIONS = """\
You are a crypto payroll agent that executes batch payments on Base and Unichain
through the Spraay Protocol Gateway.

Workflow:
1. When the user requests a payment, call `get_token_info` to confirm the token
   is supported and retrieve its decimals.
2. Convert human-readable amounts to raw base units using the token's decimals
   (e.g. 100 USDC → "100000000" with 6 decimals).
3. Call `estimate_batch` so the user can review gas and fees before committing.
4. Only after the user confirms, call `execute_batch` to produce the unsigned
   transaction. Remind them it must be signed and broadcast on-chain.
5. After they submit the transaction, use `check_transaction` to verify it landed.

Important:
- All amounts must be in raw base units (no decimals). Double-check conversions.
- Maximum 200 recipients per batch. For larger payrolls, split across batches.
- The protocol charges a 0.3% fee on each batch, deducted on-chain.
- execute_batch returns an UNSIGNED transaction — no funds move until signed.
- Always show the user the estimate before executing.
"""


def create_payroll_agent(
    api_key: str | None = None,
    model: str | None = None,
) -> Agent:
    """Create and return a configured payroll agent.

    Args:
        api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        model: Model name. Falls back to OPENAI_MODEL env var (default: gpt-4o).

    Returns:
        A configured Agent instance ready to handle payroll tasks.
    """
    client = AsyncOpenAI(api_key=api_key or OPENAI_API_KEY)

    agent = Agent(
        client=client,
        model=model or OPENAI_MODEL,
        name="PayrollAgent",
        instructions=SYSTEM_INSTRUCTIONS,
        tools=[estimate_batch, execute_batch, get_token_info, check_transaction],
        before_tool_callback=before_tool_check,
    )

    return agent
