# Tempus SDK (Node.js)

Tempus is the definitive ledger that proves exactly **why** an AI agent took an action, sealing it with a cryptographic HMAC-SHA256 receipt.

Integrate Tempus into your TS/JS corporate AI agents in **5 minutes**.

## Installation

```bash
npm install tempus-sdk
```

## Quick Start (5-Minute Integration)

Wrap your AI agent's decision logic with Tempus to secure it and generate a cryptographic audit trail.

```typescript
import { TempusClient } from 'tempus-sdk';

// 1. Initialize the client (automatically uses process.env.TEMPUS_API_KEY)
const tempus = new TempusClient({ baseURL: 'http://localhost:8001' });

async function evaluateLoan(userProfile) {
  // 2. Define your agent's context and input
  const decisionPayload = {
    agent_id: 'loan-assessor-ai',
    rule_name: 'credit_policy_v1',
    context: { doc: 'user_profile_123' },
    input_data: { credit_score: userProfile.score, amount: 50000 }
  };

  // 3. Let Tempus evaluate the rule and seal it cryptographically
  const { decision, receipt } = await tempus.govern.decide(decisionPayload);

  console.log("Decision Approved:", decision.approved);
  console.log("Cryptographic Receipt (HMAC-SHA256):", receipt);
  
  return decision;
}
```

## Why Tempus?
- **Auditoría:** Mathematically prove your AI's decisions to auditors.
- **Sello Criptográfico:** `receipt` is an HMAC-SHA256 hash. Real-time Tamper detection.
- **MICA & AI Act Compliant:** Full deterministic tracing of AI behavior.
