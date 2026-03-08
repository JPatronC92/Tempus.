# The Decision Database (DBD) 🛡️🏛️

> **The first flight recorder for Autonomous AI Agents.**

[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](./LICENSE)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js-black.svg)](https://nextjs.org/)
[![Rust](https://img.shields.io/badge/Engine-Rust-orange.svg)](https://www.rust-lang.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)

**AI models hallucinate. Software shouldn't.** Tempus is a new primitive in the AI infrastructure stack: a **Decision Database** that guarantees traceability, determinism, and cryptographic inmutability for any action taken by an AI agent.

---

## 🚀 The Vision
While traditional databases (PostgreSQL) store *state* and vector databases (Qdrant) store *semantic context*, **DBD stores why your systems act**. 

In an era of autonomous agents, corporate liability depends on proving that every decision was filtered through deterministic rules and sealed against tampering.

## 🛠️ Key Components
- **Tempus Engine (Core):** High-performance Rust & WASM engine for deterministic rule evaluation (Rule Logic).
- **Semantic Motor Seeker:** Hybrid search engine to retrieve the context needed for governance.
- **Decision Explorer:** A real-time visual timeline to audit and verify cryptographic receipts.
- **Cryptographic Receipts:** HMAC-SHA256 signatures that seal the causal chain (Agent -> Input -> Rule -> Output).

## 📂 Repository Structure
```bash
/DBD
├── Agent-Orchestrator      # Sample agent scripts and demos
├── Semantic-motor-seeker   # Vector memory and hybrid search (FastAPI/Qdrant)
├── Tempus-Engine           # The Governance Kernel (Python/Rust/WASM)
│   ├── tempus-dashboard    # Next.js Explorer & Pitch Deck
│   ├── tempus_core         # Rust rule engine (The Brain)
│   └── tempus_wasm         # Compiled WASM for browser-side governance
├── scripts                 # Tamper & Performance demos
└── docker-compose.yml      # The "Motherboard" - Spin up the whole infra
```

## 🎙️ Live Demo (Try it out!)
1. **Spin up the stack:**
   ```bash
   docker compose up -d
   ```
2. **Open the Dashboard:** Go to `http://localhost:3000/explorer`
3. **Trigger an Action:** Click on **⚡ Trigger Agent Action** to see real-time governance.
4. **Audit the Trace:** Select any decision and check the **Causal Trace**.
5. **Verify Security:** Run `python scripts/tamper_demo.py` and see the auditor turn red.

## ⚖️ Governance & Auditing
Every decision generates a receipt that can be verified mathematically.
- `GET /api/v1/govern/audit/{receipt}`: Rebuilds the hash to detect database manipulation.
- `GET /api/v1/govern/explain/{receipt}`: Decodes the causal logic behind an action.

## 📜 License
This project is **Proprietary**. For commercial use, contact [JPatronC92](https://github.com/JPatronC92). See [LICENSE](./LICENSE) for details.

---
*Developed by JPatronC92 - 2026*
