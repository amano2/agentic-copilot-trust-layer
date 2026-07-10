# DEMO_SCRIPT.md — Walkthrough & Narrative
## Project: Agentic Enterprise Copilot with Trust Layer
## System Domain: Insurance FNOL (First Notice of Loss)

This script provides a 5–10 minute end-to-end demonstration flow for pitch and validation meetings.

---

### MAPPING TO BLUEVERSE ENTERPRISE AI CONCEPTS
1. **Agent Builder & Graph (LangGraph)** ➔ **"Foundry" Equivalent**
   - Coordinates the supervisor router, structured database retrieval, and unstructured policy document retrieval.
2. **Trust Layer & Human-in-the-Loop Queue** ➔ **"RightAction" Equivalent**
   - Executes self-consistency checking (two independent reasoning passes) and routes low-confidence or ambiguous claims to human reviews.

---

### DEMO NARRATIVE FLOW

#### Step 1: Establish the Regulated Domain Framing
> **Demonstrator Speech:**
> *"Before we begin, it is critical to establish that this system is built strictly as a **decision-support tool with mandatory human sign-off**, not an autonomous claim approver. In a highly regulated environment like insurance or banking, letting an AI make final high-stakes determinations autonomously carries extreme compliance risks. That is why our **RightAction** trust layer is designed to act as a safeguard—auto-flagging anything ambiguous and requiring human confirmation."*

#### Step 2: Ingest and Trigger Pipeline Core (Foundry)
- Open the dashboard at `http://localhost:5173`.
- Point out the **Ingested Claims Database** table showing claims that have arrived via the FNOL intake.
- Click **"Run Pipeline"** on **Claim CLM-003 (Charlie Ding)**.
> **Demonstrator Speech:**
> *"Here, we are triggering our **Foundry** orchestrator. The supervisor agent checks the state, retrieves the structured claim metadata, queries our ChromaDB vector database for policy terms, and forwards the entire context to our compliance model, `nvidia/nemotron-3-ultra-550b-a55b:free`."*

#### Step 3: Observe the Live Trace and Trust Scoring (RightAction)
- Click **"Review Details"** (Adjudicate) on CLM-003 to open the side panel.
- Point out the **Foundry Engine Node Timeline** (timeline trace showing `intake` ➔ `retrieve_structured` ➔ `retrieve_unstructured` ➔ `reasoning` ➔ `decision`).
> **Demonstrator Speech:**
> *"We can watch the exact node-by-node timeline traces live, showing inputs, outputs, and latencies. For Charlie Ding's claim, the system retrieved policy rules and ran two independent reasoning passes (Self-Consistency evaluation). Because Charlie was driving for Uber—which is a personal auto policy violation—the two reasoning models evaluated the exclusion and marked the claim as PENDING_HUMAN_REVIEW with a 50% trust score."*

#### Step 4: The Live "Gotcha" Case (The Safe Route)
- Highlight the **Retrieved Policy Sources** tab, pointing to:
  - `policy_auto_accident.txt`
  - `policy_commercial_use.txt`
> **Demonstrator Speech:**
> *"This is our live 'gotcha' case. The claimant's description mentions 'rideshare shift,' but the structured policy shows a personal auto plan. Our trust layer caught this contradiction. Instead of confidently guessing, it flagged it, lowered the confidence score, and automatically routed it to our review queue rather than auto-finalizing it."*

#### Step 5: Human Adjudication (Closing the Loop)
- In the side drawer, input the following review note:
  - *“Claimant confirmed commercial activity (rideshare) without commercial rider endorsement. Claim rejected under SEC-105 commercial use exclusion.”*
- Click **"Reject Claim"**.
- Observe the status updating live to **REJECTED** in the database table.
> **Demonstrator Speech:**
> *"With a single click, the human reviewer adjudicates the claim. The system updates the claim record and appends a human adjudication log to the audit history. The review queue is now clear. We have achieved complete regulatory safety with agentic efficiency."*
