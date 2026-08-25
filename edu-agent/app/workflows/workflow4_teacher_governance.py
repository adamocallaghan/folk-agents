from __future__ import annotations

import json
import uuid
import datetime
from typing import Dict, Any

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.genai import types

from app.tools.firebase_tools import fetch_student_profile, persist_teacher_approval
from app.firebase_service import firestore_service

import os

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")


async def generate_remediation_proposal_tool(
    student_id: str,
    identified_gaps: str,
    proposed_rules_json: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Stages a formal remediation plan awaiting teacher HITL approval.

    Args:
        student_id: The ID of the student.
        identified_gaps: Comma-separated summary of learning gaps.
        proposed_rules_json: JSON list of proposed intervention rules.

    Returns:
        Dict with generated plan_id and staged plan details.
    """
    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
    try:
        rules = json.loads(proposed_rules_json)
    except Exception:
        rules = [{"rule_id": "rule_1", "action_type": "insert_visual_scaffold", "description": proposed_rules_json}]

    gaps = [g.strip() for g in identified_gaps.split(",") if g.strip()]

    plan = {
        "plan_id": plan_id,
        "student_id": student_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "identified_learning_gaps": gaps,
        "proposed_interventions": rules,
        "status": "proposed",
        "expected_outcome": "Accelerate conceptual mastery through targeted visual & analogy scaffolding",
    }

    # Store staged plan in session state and in Firestore pending queue
    tool_context.state[f"staged_plan_{plan_id}"] = plan
    await firestore_service.save_document("remediation_plans", plan_id, plan)

    return {
        "status": "staged_for_approval",
        "plan_id": plan_id,
        "plan": plan,
        "message": f"Remediation plan {plan_id} created and staged for teacher review.",
    }


teacher_governance_instruction = """
You are "Athena", a Collaborative Teacher Copilot and Pedagogical Strategist.

Your mission:
1. **Longitudinal Profile Ingestion**: Review the student's longitudinal cognitive profile, mastery map, and recurring friction points (using `fetch_student_profile` or `{student_profile}`).
2. **Interactive Discovery Dialogue**: Engage in a rich, multi-turn professional dialogue with the educator:
   - Highlight emerging trends (e.g. "Student struggles when moving from ATP definitions to chemical formulas").
   - Offer targeted macro-remediation options (e.g., global scaffolding rules, prerequisite warm-up exercises, visual-first explanations).
3. **Draft Remediation Plans**: Propose concrete intervention rules using `generate_remediation_proposal_tool`.
4. **Human-In-The-Loop (HITL) Governance**: Explicitly ask for the teacher's approval or modifications. When the teacher confirms ("Approve", "Yes, proceed with this plan", or gives custom edits), invoke `persist_teacher_approval` to lock and persist the changes to Firestore.

Context:
- Current Student ID: {student_id}
- Active Remediation Proposals: {active_remediations}
"""

teacher_discovery_agent = Agent(
    name="teacher_discovery_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=teacher_governance_instruction,
    description="Collaborative teacher discovery and HITL governance agent that designs remediation strategies and awaits teacher sign-off.",
    tools=[
        fetch_student_profile,
        generate_remediation_proposal_tool,
        persist_teacher_approval,
    ],
    output_key="teacher_discovery_response",
)
