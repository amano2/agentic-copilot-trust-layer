import os
import sys
import re
from typing import Dict, List, Any, Tuple

# Add parent backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from agents.llm_client import call_llm

def parse_reasoning_output(text: str) -> Tuple[str, str, str]:
    """
    Parses LLM output to extract Decision, Confidence level, and Rationale.
    """
    decision_match = re.search(r"DECISION:\s*(APPROVED|REJECTED|PENDING_HUMAN_REVIEW)", text, re.IGNORECASE)
    confidence_match = re.search(r"CONFIDENCE:\s*(HIGH|MEDIUM|LOW)", text, re.IGNORECASE)
    
    decision = decision_match.group(1).upper() if decision_match else "PENDING_HUMAN_REVIEW"
    confidence = confidence_match.group(1).upper() if confidence_match else "LOW"
    
    # Rationale is the text after RATIONALE:
    rationale_split = re.split(r"RATIONALE:\s*", text, flags=re.IGNORECASE)
    rationale = rationale_split[1].strip() if len(rationale_split) > 1 else text.strip()
    
    return decision, confidence, rationale

def run_reasoning_pass(structured_info: str, policy_chunks: str, pass_num: int, temperature: float) -> Tuple[str, str, str, str]:
    """
    Runs a single LLM reasoning pass with a specific temperature and prompt framing.
    """
    prompt_framing = ""
    if pass_num == 2:
        prompt_framing = (
            "\nNote: This is an independent verification pass. Double-check all date limits, "
            "exhibits, and exclusion riders strictly. Do not guess."
        )

    system_prompt = (
        "You are the Core Compliance & Reasoning Specialist for an insurance company's First Notice of Loss (FNOL) decision system.\n"
        "Your task is to evaluate an insurance claim based on the provided structured record and unstructured policy rules.\n\n"
        "Apply the policy rules carefully:\n"
        "- If the incident and claim details violate any exclusion (e.g. commercial use like Uber, gradual leak, late filing, or missing police reports), you must REJECT the claim or route to PENDING_HUMAN_REVIEW.\n"
        "- If all conditions are satisfied, you should APPROVE the claim.\n"
        "- If there is contradictory information, missing required documentation, or ambiguity (e.g. late filing with a valid hospital waiver), you must route the claim to PENDING_HUMAN_REVIEW.\n"
        f"{prompt_framing}\n\n"
        "You MUST respond in the following exact format (do not deviate):\n"
        "DECISION: <APPROVED, REJECTED, or PENDING_HUMAN_REVIEW>\n"
        "CONFIDENCE: <HIGH, MEDIUM, or LOW>\n"
        "RATIONALE:\n"
        "<provide a clear, numbered step-by-step reasoning explaining why the decision was reached, referencing specific policy documents and claim parameters>"
    )
    
    user_prompt = f"""
=== CLAIM RECORD (STRUCTURED) ===
{structured_info}

=== RELEVANT INSURANCE POLICY CLAUSES ===
{policy_chunks}

Please analyze this claim and provide your decision and step-by-step rationale.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # We call the reasoning model
    # Primary reasoning model is nvidia/nemotron-3-ultra-550b-a55b:free
    raw_response = call_llm(messages, role="reasoning", temperature=temperature)
    decision, confidence_str, rationale = parse_reasoning_output(raw_response)
    
    return decision, confidence_str, rationale, raw_response

def evaluate_trust(structured_data: Dict[str, Any], unstructured_context: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Executes self-consistency scoring by running the reasoning agent twice
    and comparing outputs to establish a confidence score.
    """
    import json
    structured_info = json.dumps(structured_data, indent=2)
    
    policy_chunks = ""
    for idx, match in enumerate(unstructured_context):
        policy_chunks += f"\n[Policy Source {idx+1} - File: {match['metadata']['source_file']}]\n{match['content']}\n"
        
    print("[Trust Layer] Executing Pass 1 (Temperature = 0.1)...")
    dec1, conf1, rat1, raw1 = run_reasoning_pass(structured_info, policy_chunks, pass_num=1, temperature=0.1)
    print(f"[Trust Layer] Pass 1 Result: {dec1} (Self-reported confidence: {conf1})")
    
    print("[Trust Layer] Executing Pass 2 (Temperature = 0.7)...")
    dec2, conf2, rat2, raw2 = run_reasoning_pass(structured_info, policy_chunks, pass_num=2, temperature=0.7)
    print(f"[Trust Layer] Pass 2 Result: {dec2} (Self-reported confidence: {conf2})")
    
    # Derive confidence score based on self-consistency agreement
    passes = [
        {"pass_index": 1, "decision": dec1, "confidence": conf1, "rationale": rat1, "raw_response": raw1},
        {"pass_index": 2, "decision": dec2, "confidence": conf2, "rationale": rat2, "raw_response": raw2}
    ]
    
    if dec1 == dec2:
        if dec1 in ["APPROVED", "REJECTED"]:
            confidence_score = 1.0 # High confidence agreement
            final_decision = dec1
            final_rationale = rat1
        else: # Both agreed on PENDING_HUMAN_REVIEW
            confidence_score = 0.5 # Agreed complexity
            final_decision = "PENDING_HUMAN_REVIEW"
            final_rationale = f"Both reasoning runs agree this case requires human manager review. Details:\n\n{rat1}"
    else:
        # Disagreement between runs!
        confidence_score = 0.0 # High ambiguity
        final_decision = "PENDING_HUMAN_REVIEW"
        final_rationale = (
            f"WARNING: The automated reasoning system failed to reach consensus (Self-Consistency Mismatch).\n"
            f"Run 1 concluded: {dec1}\n"
            f"Run 2 concluded: {dec2}\n\n"
            f"Run 1 Rationale:\n{rat1}\n\n"
            f"Run 2 Rationale:\n{rat2}"
        )
        
    return {
        "decision": final_decision,
        "confidence_score": confidence_score,
        "rationale": final_rationale,
        "passes": passes
    }
