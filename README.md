<div align="center">

# 🛡️ Agentic Enterprise Copilot · Trust Layer

**A production-grade, human-in-the-loop decision support system for regulated insurance claims.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-FF6B35?style=for-the-badge&logo=chainlink&logoColor=white)](https://langchain-ai.github.io/langgraph)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorStore-FF6B6B?style=for-the-badge&logo=databricks&logoColor=white)](https://trychroma.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Free_LLMs-7C3AED?style=for-the-badge&logo=openai&logoColor=white)](https://openrouter.ai)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)

> ⚠️ **This is a decision-support tool with mandatory human sign-off — not an autonomous approver.**  
> Every high-stakes routing decision requires explicit reviewer adjudication before finalization.

</div>

---

## 📌 Overview

This system orchestrates multiple specialized AI agents using a **LangGraph supervisor pattern** to pre-screen insurance **First Notice of Loss (FNOL)** claims. It evaluates incoming claims against structured SQL records and a hybrid vectorstore of policy documents, computes a dual-pass self-consistency trust score, runs a compliance challenger audit, and routes low-confidence or ambiguous cases to a human reviewer queue.

---

## 🗺️ BlueVerse Enterprise Mapping

| 🏗️ Regulated AI Component | 🔷 BlueVerse Concept | ⚙️ Technical Implementation |
|:---|:---|:---|
| **Agent Builder & Graph** | **Foundry** | [LangGraph](https://langchain-ai.github.io/langgraph) orchestration with async parallel retrieval, loopback suspension, and challenger audit nodes |
| **Trust & Safeguard Layer** | **RightAction** | Dual-pass self-consistency scorer + human-in-the-loop review queue + side-by-side contradiction diff viewer |

---

## 🏛️ System Architecture

The upgraded async LangGraph pipeline:

```
                    📥 [Ingested Claim ID]
                           │
                           ▼
                     🔍 [Intake Node]
                      (Load claim record)
                           │
                           ▼
               ⚡ [Concurrent Retrieve Node]
               (SQL + ChromaDB hybrid search)
                           │
                           ▼
                    🔎 [Eval State Node]
                     (Validate completeness)
                          / \
                         /   \
              (Missing)        (Complete)
                 /                  \
   ⏸️ [Loopback Request]    🧠 [Reasoning Node]
   (AWAITING_DOCUMENT)    (Self-Consistency)
          │                       │
          │                       ▼
          │               ⚔️ [Challenger Node]
          │                (Compliance Audit)
          │                       │
          └──────────┬────────────┘
                     ▼
             ✅ [Decision Node]
        (Write to DB · Emit trace logs)
```

---

## ✨ Key Enterprise Features

### 🔒 Trust & Compliance
- **⚔️ Challenger Compliance Auditor** — A dedicated LangGraph node that audits the primary reasoning recommendation against policy exclusion codes (e.g. `SEC-105` rideshare, `SEC-102` gradual leak). On mismatch, it overrides confidence to `0.0` and routes to human review.
- **🔁 Conversational Loopbacks** — The pre-check `eval_state` node validates critical fields. Claims with missing loss amounts (e.g. `CLM-006`, `$0.0`) are auto-suspended with status `AWAITING_DOCUMENT` before any LLM calls are made.
- **🎯 Dual-Pass Self-Consistency** — Reasoning runs twice at temperatures `0.1` (deterministic) and `0.7` (exploratory). Diverging conclusions collapse the trust score to `0.0` and trigger human queue routing.

### 🔍 Retrieval & Reasoning
- **🧩 Hybrid Dense + Sparse Search** — Combines [ChromaDB](https://trychroma.com) semantic vectors (via `all-MiniLM-L6-v2`) with TF-IDF sparse token matching on policy exclusion codes, then reranks with a local [`cross-encoder/ms-marco-MiniLM-L-6-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2).
- **⚡ Parallel Async Execution** — All graph nodes are `async def` with blocking SQL and ChromaDB queries wrapped in `asyncio.to_thread`, halving pipeline latency.

### 📊 Observability & UI
- **📡 WebSocket Live Pipeline HUD** — [FastAPI](https://fastapi.tiangolo.com) broadcasts node transitions over `/api/ws`. The [React](https://react.dev) + [Vite](https://vitejs.dev) dashboard renders a frosted-glass progress timeline overlay in real time.
- **🔬 Contradiction Diff-Viewer** — Side-by-side panel highlighting exact trigger terms (e.g. `Uber`, `rideshare`, `no police report`) overlapping in both the claimant's statement and the matched policy clause.

---

## 🧪 Stress Test Results

All 6 seeded claims run through the full pipeline end-to-end:

| Claim | Claimant | Scenario | Trust Score | Decision | Queue? |
|:---:|:---|:---|:---:|:---|:---:|
| `CLM-001` | Alice Vance | ✅ Normal auto accident — rear-ended at light | `0.5` | `PENDING_HUMAN_REVIEW` | ✅ Yes |
| `CLM-002` | Bob Miller | ⚠️ Gradual pipe leak — multi-month delay (SEC-102) | `0.0` | `PENDING_HUMAN_REVIEW` | ✅ Yes (Challenger) |
| `CLM-003` | Charlie Ding | 🚗 Ridesharing while online (Uber) — SEC-105 exclusion | `0.0` | `PENDING_HUMAN_REVIEW` | ✅ Yes (Challenger) |
| `CLM-004` | Diana Prince | 🔥 Late fire claim — hospitalized (SEC-106 waiver) | `0.5` | `PENDING_HUMAN_REVIEW` | ✅ Yes |
| `CLM-005` | Evan Wright | 🔐 Theft — no police report filed (SEC-103) | `0.0` | `PENDING_HUMAN_REVIEW` | ✅ Yes (Disagreement) |
| `CLM-006` | Frank Miller | ❌ Missing loss amount — `$0.0` entered | `0.0` | `AWAITING_DOCUMENT` | ⏸️ Suspended |

---

## 🚀 Getting Started

### 📋 Prerequisites

| Tool | Version | Link |
|:---|:---|:---|
| 🐍 Python | 3.10+ | [python.org](https://python.org) |
| 🟢 Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| 🐳 Docker | Latest (optional) | [docker.com](https://docker.com) |
| 🔑 OpenRouter API Key | Free tier works | [openrouter.ai/keys](https://openrouter.ai/keys) |

### ⚡ Quick Start (Local Development)

**1. Configure Environment**

Copy the example env file and add your [OpenRouter](https://openrouter.ai) API key:
```bash
cp backend/.env.example backend/.env
```
```env
OPENROUTER_API_KEY=your_openrouter_key_here
```

**2. Seed Database & Vector Store**

Installs dependencies and seeds SQLite + ChromaDB with 6 claims and 8 policy documents:
```bash
pip install -r backend/requirements.txt
python backend/synthetic_data/generate_synthetic.py
```

**3. Start the Backend API**

```bash
python backend/api/main.py
```
> 🌐 FastAPI server starts at **`http://localhost:8000`** · Swagger UI at **[`/docs`](http://localhost:8000/docs)**

**4. Start the Frontend Dashboard**

```bash
cd frontend
npm install
npm run dev
```
> 🎨 Liquid-glass React dashboard at **`http://localhost:5173`**

---

## 🐳 Docker Deployment (One-Command)

Spin up **PostgreSQL + ChromaDB + FastAPI Backend + React Frontend** in one shot:

```bash
docker-compose up --build
```

> 💡 Export your API key in the terminal before running:
> ```bash
> export OPENROUTER_API_KEY=your_key_here   # Linux/macOS
> set OPENROUTER_API_KEY=your_key_here      # Windows CMD
> ```

---

## 🗂️ Repository Structure

```
📦 agentic-copilot-trust-layer
 ┣ 📂 backend
 ┃  ┣ 📂 agents          ← LangGraph nodes (intake, retrieve, reasoning, challenger, decision)
 ┃  ┣ 📂 trust           ← Self-consistency confidence scoring engine
 ┃  ┣ 📂 db              ← SQLAlchemy models, migrations, PostgreSQL/SQLite fallback
 ┃  ┣ 📂 vectorstore     ← ChromaDB setup, hybrid search, cross-encoder reranking
 ┃  ┣ 📂 api             ← FastAPI routes + WebSocket connection manager
 ┃  ┗ 📂 synthetic_data  ← Claim generators + 8 policy document corpus
 ┣ 📂 frontend
 ┃  ┗ 📂 src
 ┃     ┣ 📂 components   ← AgentTraceView, ConfidenceBadge, SourcePanel, CaseDetail
 ┃     ┗ 📂 pages
 ┣ 🐳 docker-compose.yml
 ┣ 📖 README.md
 ┗ 📋 DEMO_SCRIPT.md
```

---

## 🛡️ Security

- 🔒 `.env` files are **excluded from version control** via `.gitignore`
- 📄 Only `backend/.env.example` (with placeholder values) is committed to the repo
- 🔑 API keys are loaded at runtime via `python-dotenv` and never hardcoded

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">

**Built with 🧠 LangGraph · ⚡ FastAPI · ⚛️ React · 🔍 ChromaDB · 🤖 OpenRouter**

</div>
