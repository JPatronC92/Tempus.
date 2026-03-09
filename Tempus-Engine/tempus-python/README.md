# Tempus SDK (Python)

Tempus is the definitive ledger that proves exactly **why** an AI agent took an action, sealing it with a cryptographic HMAC-SHA256 receipt.

Integrate Tempus into your Python AI agents in **5 minutes**.

## Installation

```bash
pip install tempus-sdk
```

## Quick Start (5-Minute Integration)

Wrap your AI agent's decision logic with Tempus to secure it and generate a cryptographic audit trail.

```python
import os
from tempus_sdk import TempusClient

# 1. Initialize the client (automatically uses os.environ.get("TEMPUS_API_KEY"))
tempus = TempusClient(base_url="http://localhost:8001")

def evaluate_loan(user_profile):
    # 2. Define your agent's context and input
    decision_payload = {
        "agent_id": "loan-assessor-ai",
        "rule_name": "credit_policy_v1",
        "context": {"doc": "user_profile_123"},
        "input_data": {"credit_score": user_profile["score"], "amount": 50000}
    }

    # 3. Let Tempus evaluate the rule and seal it cryptographically
    response = tempus.govern.decide(**decision_payload)

    print(f"Decision: {response.decision}")
    print(f"Cryptographic Receipt (HMAC-SHA256): {response.receipt}")
    
    return response.decision
```

## Why Tempus?
- **Auditoría:** Mathematically prove your AI's decisions to auditors.
- **Sello Criptográfico:** `receipt` is an HMAC-SHA256 hash. Real-time Tamper detection.
- **MICA & AI Act Compliant:** Full deterministic tracing of AI behavior.
