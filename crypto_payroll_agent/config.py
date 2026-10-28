"""Configuration for the Spraay Protocol Gateway."""

import os

from dotenv import load_dotenv

load_dotenv()

# Spraay Protocol Gateway
GATEWAY_BASE_URL = os.getenv("SPRAAY_GATEWAY_URL", "https://gateway.spraay.app")

# Supported chains
CHAINS = {
    "base": {"chain_id": 8453, "contract": "0x1646452F98E36A3c9Cfc3eDD8868221E207B5eEC"},
    "unichain": {"chain_id": 130, "contract": "0x08fA5D1c16CD6E2a16FC0E4839f262429959E073"},
}

# Protocol fee: 0.3% (30 basis points)
PROTOCOL_FEE_BPS = 30

# Gateway limits
MAX_RECIPIENTS_PER_BATCH = 200

# Guardrail defaults (override via env)
MAX_BATCH_USD = float(os.getenv("MAX_BATCH_USD", "10000"))
MAX_RECIPIENTS = int(os.getenv("MAX_RECIPIENTS", "200"))

# OpenAI-compatible model config (for Agent)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Block explorer
BASE_EXPLORER_URL = "https://basescan.org"
UNICHAIN_EXPLORER_URL = "https://uniscan.xyz"
