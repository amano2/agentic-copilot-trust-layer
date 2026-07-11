# Agentic Enterprise Copilot with Trust Layer

A working, production-grade decision-support copilot for regulated domains (specifically, Insurance FNOL - First Notice of Loss claims processing). This system orchestrates multiple specialized agent tasks using a supervisor pattern, evaluates claims compliance against structured SQL records and hybrid vectorstore policy clauses, computes a self-consistency score, performs a compliance challenge audit, and routes low-confidence/ambiguous cases to a human review queue.

---

## 1. MAPPING TO BLUEVERSE ENTERPRISE CONCEPT

| Regulated AI Component | BlueVerse Brand Mapping | Technical Implementation |
|---|---|---|
| **Agent Builder & Graph** | **Foundry** | LangGraph orchestration node workflow with async parallel retrieve, loopback request, and challenger node audits. |
| **Trust & Safeguard Layer** | **RightAction** | Dual-pass self-consistency agreement checker + human-in-the-loop review queue + side-by-side keyword overlap highlighter. |

---

## 2. SYSTEM ARCHITECTURE

The upgraded LangGraph workflow executes as follows:

```
                    [Ingested Claim ID]
                           │
                           ▼
                     [Intake Node]
                           │
                           ▼
                [Concurrent Retrieve Node]
                 (Query SQL & Chroma DB)
                           │
                           ▼
                    [Eval State Node]
                           / \
                          /   \
                 (Missing)     (Complete)
                  /             \
       [Loopback Request]    [Reasoning Node]
     (AWAITING_DOCUMENT)   (Self-Consistency)
              │                    │
              │                    ▼
              │            [Challenger Node]
              │             (Audit Override)
              │                    │
              \                    /
               \                  /
                \                /
                 ▼              ▼
                 [Decision Node]
         (Save status & write trace logs)
```

---

## 3. KEY ENTERPRISE FEATURES

1. **Compliance Challenger Node**: Audits the primary consensus recommendation against active policy exclusions. If a commercial exclusion (ridesharing/Uber) or graduality clause triggers a mismatch, it overrides the output to `PENDING_HUMAN_REVIEW` with `0.0` confidence.
2. **Conversational Loopbacks**: Validates fields in the pre-check node. Claims with missing data (e.g. `$0.0` estimated loss for `CLM-006`) bypass reasoning and auto-suspend with status `AWAITING_DOCUMENT`.
3. **Hybrid Search & Cross-Encoder Reranking**: Merges dense semantic searches with sparse token matching (prioritizing exclusion codes like `SEC-105`), and ranks the combined pool using `cross-encoder/ms-marco-MiniLM-L-6-v2`.
4. **WebSocket Streaming HUD**: Backend broadcasts node transitions live over a `/api/ws` channel. The frontend React dashboard displays a frosted glass progress timeline overlay in real-time.
5. **Highlighter Diff-Viewer**: Highlights exact overlapping risk factors (such as the word "Uber" or "rideshare") side-by-side in the claim statements and policy documentation.

---

## 4. GETTING STARTED

### Prerequisites
- Node.js (v18+)
- Python 3.10+
- Docker & Docker Compose (optional, for containerized services)

### Quick Start (Local Development)

1. **Configure Environment:**
   Create a `.env` file in the `backend/` directory cloned from `backend/.env.example` and set your OpenRouter API Key:
   ```env
   OPENROUTER_API_KEY=your_openrouter_key
   ```

2. **Seed Database & Vector Store:**
   Installs libraries and seeds the database with 6 distinct test claims and 8 policy text files.
   ```bash
   pip install -r backend/requirements.txt
   python backend/synthetic_data/generate_synthetic.py
   ```

3. **Run Backend API Server:**
   ```bash
   python backend/api/main.py
   ```
   *FastAPI server exposes endpoints on `http://localhost:8000` (Redirects to Swagger API docs at `/docs` on root load).*

4. **Run Frontend Dashboard:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   *Dashboard runs on `http://localhost:5173`*

---

## 5. DOCKER DEPLOYMENT (ONE-COMMAND SETUP)

To spin up the entire multi-container environment (PostgreSQL, ChromaDB server, FastAPI backend, React frontend) with a single command:

```bash
docker-compose up --build
```
*Note: Ensure your `OPENROUTER_API_KEY` is exported in your environment terminal prior to running compose.*

