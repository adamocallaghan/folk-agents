from __future__ import annotations

import json
import datetime
from typing import Dict, Any

from google.adk.agents import Agent, SequentialAgent
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.genai import types

from app.schemas.student import SessionEvaluation, LongitudinalProfile
from app.firebase_service import firestore_service
from app.tools.firebase_tools import fetch_student_profile

import os

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")


# ============================================================================
# 1. Lesson-Level Evaluator (Short-Term Ephemeral Agent)
# ============================================================================
evaluator_instruction = """
You are the Short-Term Learning Evaluator Agent.
Your job is to analyze the student's completed session artifacts—including quiz responses, chat transcripts, questions asked, and logged confusions—to produce an immediate diagnostic evaluation.

Inputs:
- Session ID: {session_id}
- Student ID: {student_id}
- Lesson ID / Topic: {lesson_id}
- Quiz Results: {quiz_answers}
- Session Confusions Logged: {session_confusions}
- Chat Transcript Summary: {chat_transcript}

Evaluate:
1. `comprehension_score`: 0.0 to 100.0 based on quiz accuracy and conceptual clarity in chat.
2. `friction_points`: Specific sub-concepts where the student hesitated, required hints, or had misconceptions.
3. `cognitive_load_index`: Assess if the student was 'Low', 'Optimal', 'High', or 'Overloaded'.
4. `active_inquiry_level`: 'Passive', 'Moderate', or 'Highly Curious'.
5. `immediate_takeaways`: Concrete diagnostic takeaways for this specific lesson.
"""

lesson_evaluator_agent = Agent(
    name="lesson_evaluator_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=evaluator_instruction,
    description="Analyzes ephemeral session artifacts (quiz outcomes + chat history) to evaluate comprehension and friction.",
    output_schema=SessionEvaluation,
    output_key="session_evaluation",
)


# ============================================================================
# 2. Meta-Profile Synthesizer (Long-Term Longitudinal Memory Agent)
# ============================================================================
async def update_longitudinal_profile_tool(
    student_id: str,
    updated_profile_json: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Saves and synchronizes the updated longitudinal student profile across ADK user-scoped state and Firestore.

    Args:
        student_id: The ID of the student.
        updated_profile_json: The complete JSON string of the synthesized LongitudinalProfile.

    Returns:
        Confirmation dict with persistence status.
    """
    try:
        profile_data = json.loads(updated_profile_json)
    except Exception:
        profile_data = {"student_id": student_id, "raw": updated_profile_json}

    profile_data["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 1. Update ADK User-Scoped State (Cross-session memory)
    tool_context.state[f"user:profile_{student_id}"] = profile_data
    tool_context.state[f"user:reading_level"] = profile_data.get("reading_level", "Standard")
    tool_context.state[f"user:mastery_map"] = profile_data.get("mastery_map", {})

    # 2. Persist to Firestore
    await firestore_service.save_document("student_profiles", student_id, profile_data)

    return {
        "status": "success",
        "student_id": student_id,
        "total_sessions": profile_data.get("total_sessions_completed", 1),
        "message": f"Updated cross-session profile for student {student_id}.",
    }


meta_profile_instruction = """
You are the Longitudinal Meta-Profile Synthesizer Agent.
Your responsibility is to maintain the long-term, evolving cognitive and psychological profile of the student across multiple sessions.

You ingest the latest session evaluation and merge it with the student's historical cross-session profile.

Current Inputs:
- Student ID: {student_id}
- Latest Session Evaluation: {session_evaluation}
- Prior Longitudinal Profile (from User State): {user:profile_{student_id}}

Your Tasks:
1. Update concept mastery ratings in `mastery_map` (increment attempts, adjust percentage).
2. Detect recurring patterns in misconceptions across sessions.
3. Assess cognitive growth trend (e.g., 'Accelerating with visual scaffolding', 'Struggling with multi-step processes').
4. Formulate forward-looking `scaffolding_recommendations` for future curriculum generation and teaching interventions.
5. Increment `total_sessions_completed`.
6. Call `update_longitudinal_profile_tool` with the finalized profile JSON.
"""

meta_profile_agent = Agent(
    name="meta_profile_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=meta_profile_instruction,
    description="Synthesizes short-term evaluations into long-term evolving cognitive profiles using ADK user-scoped memory and Firestore.",
    tools=[fetch_student_profile, update_longitudinal_profile_tool],
    output_key="synthesized_profile_result",
)


# ============================================================================
# Full Workflow 3 Pipeline
# ============================================================================
analytics_and_memory_workflow = SequentialAgent(
    name="analytics_and_memory_workflow",
    description="Closes a learning session: Evaluates ephemeral session data -> Synthesizes long-term longitudinal profile.",
    sub_agents=[
        lesson_evaluator_agent,
        meta_profile_agent,
    ],
)
