# Agentic Enterprise Copilot with Trust Layer

A working prototype of a decision-support copilot for regulated domains (specifically, Insurance FNOL - First Notice of Loss claims processing). This system orchestrates multiple specialized agents using a supervisor pattern, evaluates claims compliance against structured DB records and vectorstore policy clauses, computes a self-consistency score, and routes low-confidence/ambiguous cases to a human review queue.

---

## 1. MAPPING TO BLUEVERSE ENTERPRISE CONCEPT

| Regulated AI Component | BlueVerse Brand Mapping | Technical Implementation |
|---|---|---|
| **Agent Builder & Graph** | **Foundry** | LangGraph orchestration node workflow (`intake` ➔ `supervisor` ➔ retrievers ➔ `reasoning` ➔ `decision`) |
| **Trust & Safeguard Layer** | **RightAction** | Dual-pass self-consistency agreement checker + human-in-the-loop review queue |

---

## 2. SYSTEM ARCHITECTURE

The workflow executes as follows:
```
[Ingested Claim ID]
       │
       ▼
   [Intake Node]
       │
       ▼
 ┌─────────────┐
 │ Supervisor  │◄────────────┐
 └──────┬──────┘             │
        ├────────────────────┼───────────────────┐
        ▼                    ▼                   │
[Structured DB]    [Chroma Policy DB]            │ (If more data needed)
  (SQLAlchemy)      (Local MiniLM Embeds)        │
        │                    │                   │
        └──────────┬─────────┘                   │
                   ▼                             │
          [Reasoning Node]                       │
        (Consensus/Consistency) ─────────────────┘
                   │
                   ▼
           [Decision Node]
           (Conf. >= 80%? Auto-Finalize : Route to Human Queue)
```

---

## 3. GETTING STARTED

### Prerequisites
- Node.js (v18+)
- Python 3.10+
- Docker & Docker Compose (optional, for full-stack service containers)

### Quick Start (Local Development)

1. **Configure Environment:**
   Fill in your OpenRouter API key in `backend/.env` (cloned from `backend/.env.example`).
   ```env
   OPENROUTER_API_KEY=your_key_here
   ```

2. **Seed Databases:**
   Install backend dependencies and run the seeder script to initialize SQLite and ChromaDB.
   ```bash
   pip install -r backend/requirements.txt
   python backend/synthetic_data/generate_synthetic.py
   ```

3. **Run Backend API Server:**
   ```bash
   python backend/api/main.py
   ```
   *Server will run at `http://localhost:8000`*

4. **Run Frontend Dashboard:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   *Vite dashboard will run at `http://localhost:5173`*

---

## 4. DOCKER DEPLOYMENT (ONE-COMMAND SETUP)

To spin up the entire multi-container environment (PostgreSQL, ChromaDB server, FastAPI backend, React frontend) with a single command:

```bash
docker-compose up --build
```
*Note: Ensure your `OPENROUTER_API_KEY` is exported in your environment terminal prior to running compose.*
