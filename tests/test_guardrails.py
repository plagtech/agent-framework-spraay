"""Tests for guardrail checks."""

from __future__ import annotations

import pytest

from crypto_payroll_agent.guardrails import (
    GuardrailError,
    before_tool_check,
    validate_addresses,
    validate_amounts,
    validate_recipient_count,
    validate_spend_ceiling,
)


VALID_ADDR = "0x" + "a1" * 20
VALID_ADDR_2 = "0x" + "b2" * 20


class TestValidateAddresses:
    def test_valid_addresses(self):
        validate_addresses([VALID_ADDR, VALID_ADDR_2])

    def test_invalid_address_short(self):
        with pytest.raises(GuardrailError, match="Invalid Ethereum"):
            validate_addresses(["0x123"])

    def test_invalid_address_no_prefix(self):
        with pytest.raises(GuardrailError, match="Invalid Ethereum"):
            validate_addresses(["a1" * 20])

    def test_invalid_address_bad_chars(self):
        with pytest.raises(GuardrailError, match="Invalid Ethereum"):
            validate_addresses(["0x" + "zz" * 20])

    def test_mixed_valid_invalid(self):
        with pytest.raises(GuardrailError):
            validate_addresses([VALID_ADDR, "0xbad"])


class TestValidateRecipientCount:
    def test_within_limit(self):
        validate_recipient_count([VALID_ADDR] * 200)

    def test_exceeds_limit(self):
        with pytest.raises(GuardrailError, match="Too many recipients"):
            validate_recipient_count([VALID_ADDR] * 201)

    def test_empty_list(self):
        with pytest.raises(GuardrailError, match="empty"):
            validate_recipient_count([])


class TestValidateAmounts:
    def test_valid_amounts(self):
        validate_amounts(["1000000", "2000000"], [VALID_ADDR, VALID_ADDR_2])

    def test_length_mismatch(self):
        with pytest.raises(GuardrailError, match="Mismatch"):
            validate_amounts(["1000000"], [VALID_ADDR, VALID_ADDR_2])

    def test_non_integer(self):
        with pytest.raises(GuardrailError, match="not a valid integer"):
            validate_amounts(["abc"], [VALID_ADDR])

    def test_zero_amount(self):
        with pytest.raises(GuardrailError, match="positive"):
            validate_amounts(["0"], [VALID_ADDR])

    def test_negative_amount(self):
        with pytest.raises(GuardrailError, match="positive"):
            validate_amounts(["-100"], [VALID_ADDR])


class TestValidateSpendCeiling:
    def test_under_ceiling(self):
        # 100 USDC = $100, well under $10k default
        validate_spend_ceiling("USDC", ["100000000"])

    def test_over_ceiling(self):
        # 15,000 USDC = $15k, over $10k default
        with pytest.raises(GuardrailError, match="exceeds ceiling"):
            validate_spend_ceiling("USDC", ["15000000000"])

    def test_volatile_token_skipped(self):
        # ETH has no fixed USD price — ceiling check should pass
        validate_spend_ceiling("ETH", ["100000000000000000000"])  # 100 ETH

    def test_case_insensitive(self):
        validate_spend_ceiling("usdc", ["100000000"])

    def test_unknown_token_skipped(self):
        validate_spend_ceiling("DEGEN", ["999999999999999"])


class TestBeforeToolCheck:
    def test_allows_non_batch_tools(self):
        result = before_tool_check("get_token_info", {})
        assert result is None

    def test_allows_valid_batch(self):
        result = before_tool_check(
            "estimate_batch",
            {
                "token": "USDC",
                "recipients": [VALID_ADDR],
                "amounts": ["1000000"],
            },
        )
        assert result is None

    def test_blocks_invalid_address(self):
        with pytest.raises(GuardrailError):
            before_tool_check(
                "execute_batch",
                {
                    "token": "USDC",
                    "recipients": ["0xbad"],
                    "amounts": ["1000000"],
                },
            )

    def test_blocks_over_ceiling(self):
        with pytest.raises(GuardrailError, match="exceeds ceiling"):
            before_tool_check(
                "execute_batch",
                {
                    "token": "USDC",
                    "recipients": [VALID_ADDR],
                    "amounts": ["15000000000"],
                },
            )

    def test_blocks_too_many_recipients(self):
        addrs = [f"0x{i:040x}" for i in range(201)]
        with pytest.raises(GuardrailError, match="Too many recipients"):
            before_tool_check(
                "estimate_batch",
                {
                    "token": "USDC",
                    "recipients": addrs,
                    "amounts": ["1000000"] * 201,
                },
            )
