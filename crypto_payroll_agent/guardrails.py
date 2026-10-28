"""Guardrails for the crypto payroll agent.

These checks run via MAF's `before_tool_callback` before any tool executes.
They enforce spend ceilings, recipient caps, and address validation to
prevent accidental or malicious misuse.
"""

from __future__ import annotations

import re

from crypto_payroll_agent.config import MAX_BATCH_USD, MAX_RECIPIENTS


# Matches a valid Ethereum address (0x + 40 hex chars)
ETH_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Approximate stablecoin prices for ceiling checks (conservative).
# Only used for the spend-ceiling guardrail — not for display.
APPROX_USD_PRICES = {
    "USDC": 1.0,
    "USDT": 1.0,
    "DAI": 1.0,
    "EURC": 1.1,  # conservative EUR/USD estimate
}

# Decimals per token for converting raw amounts
TOKEN_DECIMALS = {
    "ETH": 18,
    "USDC": 6,
    "USDT": 6,
    "DAI": 18,
    "EURC": 6,
    "WETH": 18,
}


class GuardrailError(Exception):
    """Raised when a guardrail check fails."""


def validate_addresses(recipients: list[str]) -> None:
    """Validate that all recipient addresses are well-formed Ethereum addresses."""
    invalid = [addr for addr in recipients if not ETH_ADDRESS_RE.match(addr)]
    if invalid:
        raise GuardrailError(
            f"Invalid Ethereum address(es): {', '.join(invalid[:5])}"
            + (f" (and {len(invalid) - 5} more)" if len(invalid) > 5 else "")
        )


def validate_recipient_count(recipients: list[str]) -> None:
    """Enforce the recipient cap (gateway max: 200)."""
    if len(recipients) > MAX_RECIPIENTS:
        raise GuardrailError(
            f"Too many recipients: {len(recipients)} exceeds limit of {MAX_RECIPIENTS}. "
            f"Split into batches of {MAX_RECIPIENTS} or fewer."
        )
    if len(recipients) == 0:
        raise GuardrailError("Recipients list is empty.")


def validate_amounts(amounts: list[str], recipients: list[str]) -> None:
    """Validate amounts are positive integers and match recipients length."""
    if len(amounts) != len(recipients):
        raise GuardrailError(
            f"Mismatch: {len(amounts)} amounts for {len(recipients)} recipients."
        )
    for i, amt in enumerate(amounts):
        try:
            val = int(amt)
        except (ValueError, TypeError):
            raise GuardrailError(
                f"Amount at index {i} is not a valid integer: {amt!r}"
            )
        if val <= 0:
            raise GuardrailError(
                f"Amount at index {i} must be positive, got {val}."
            )


def validate_spend_ceiling(token: str, amounts: list[str]) -> None:
    """Check that total batch value stays under the configured USD ceiling.

    Only enforced for tokens with known USD prices (stablecoins).
    For volatile tokens (ETH, WETH), the ceiling is skipped — the
    human-approval gate on execute_batch is the safeguard.
    """
    token_upper = token.upper()
    price = APPROX_USD_PRICES.get(token_upper)
    if price is None:
        return  # volatile token — rely on approval_mode="always_require"

    decimals = TOKEN_DECIMALS.get(token_upper, 18)
    total_raw = sum(int(a) for a in amounts)
    total_usd = (total_raw / (10**decimals)) * price

    if total_usd > MAX_BATCH_USD:
        raise GuardrailError(
            f"Batch total ~${total_usd:,.2f} exceeds ceiling of ${MAX_BATCH_USD:,.2f}. "
            f"Raise MAX_BATCH_USD or split into smaller batches."
        )


def before_tool_check(tool_name: str, tool_input: dict) -> dict | None:
    """MAF before_tool_callback — runs before each tool invocation.

    Returns None to allow the call, or raises GuardrailError to block it.

    Usage with Agent:
        agent = Agent(
            ...,
            before_tool_callback=before_tool_check,
        )
    """
    batch_tools = {"estimate_batch", "execute_batch"}

    if tool_name not in batch_tools:
        return None

    recipients = tool_input.get("recipients", [])
    amounts = tool_input.get("amounts", [])
    token = tool_input.get("token", "")

    validate_recipient_count(recipients)
    validate_addresses(recipients)
    validate_amounts(amounts, recipients)
    validate_spend_ceiling(token, amounts)

    return None
