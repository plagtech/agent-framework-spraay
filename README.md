# agent-framework-spraay

Crypto payroll agent for [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) using the [Spraay Protocol Gateway](https://spraay.app).

Executes batch ERC-20 and native ETH payments on **Base** and **Unichain** through a single agent conversation — estimate fees, review, execute, and verify on-chain.

## Architecture

```
User → Agent (LLM) → MAF Tools → Spraay Gateway → Unsigned Tx → Sign & Broadcast
                  ↓
            Guardrails
         (before_tool_callback)
```

**Tools** (4 gateway endpoints):

| Tool | Approval | Cost | Description |
|------|----------|------|-------------|
| `get_token_info` | none | free | Supported tokens, chains, contracts |
| `estimate_batch` | none | ~$0.001 | Gas + fee estimate for a batch |
| `execute_batch` | always | ~$0.02 | Produce unsigned batch transaction |
| `check_transaction` | none | free | Verify tx status on-chain |

**Guardrails** (`before_tool_callback`):
- Recipient cap: max 200 per batch (gateway limit)
- Address validation: rejects malformed Ethereum addresses
- Spend ceiling: configurable USD cap on stablecoin batches (default $10,000)
- Amount validation: positive integers, length matches recipients

## Supported Tokens

| Token | Address | Decimals |
|-------|---------|----------|
| ETH | native | 18 |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 6 |
| USDT | `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2` | 6 |
| DAI | `0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb` | 18 |
| EURC | `0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42` | 6 |
| WETH | `0x4200000000000000000000000000000000000006` | 18 |

Any ERC-20 on Base or Unichain is supported via contract address.

## Supported Chains

| Chain | Chain ID | Contract |
|-------|----------|----------|
| Base | 8453 | `0x1646452F98E36A3c9Cfc3eDD8868221E207B5eEC` |
| Unichain | 130 | `0x08fA5D1c16CD6E2a16FC0E4839f262429959E073` |

## Setup

```bash
git clone https://github.com/plagtech/agent-framework-spraay.git
cd agent-framework-spraay
pip install -e ".[dev]"
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

## Usage

```python
from crypto_payroll_agent import create_payroll_agent

agent = create_payroll_agent()

# Run the agent with a payroll task
response = await agent.run(
    "Pay 100 USDC each to these three wallets: "
    "0xAlice..., 0xBob..., 0xCharlie..."
)
```

The agent will:
1. Look up USDC token info and decimals
2. Convert 100 USDC → `"100000000"` (6 decimals)
3. Estimate gas and fees for the batch
4. Ask for human approval (enforced by `approval_mode="always_require"`)
5. Return the unsigned transaction for signing

### Custom guardrail limits

```python
import os

os.environ["MAX_BATCH_USD"] = "50000"   # raise ceiling to $50k
os.environ["MAX_RECIPIENTS"] = "100"     # lower recipient cap

agent = create_payroll_agent()
```

## Tests

```bash
pytest
```

Tests mock all gateway HTTP calls with `respx` — no real network requests, no API keys needed.

## Fee Disclosure

The Spraay Protocol Gateway charges a **0.3% fee** (30 basis points) on each batch payment, deducted on-chain when the transaction executes. Gateway API calls use the [x402 payment protocol](https://www.x402.org/) — estimates cost ~$0.001 and execution calls cost ~$0.02.

This agent produces **unsigned transactions**. No funds move until the sender signs and broadcasts the transaction on-chain.

## License

MIT
