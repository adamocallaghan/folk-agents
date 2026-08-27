from __future__ import annotations

import json
import logging
from typing import Dict, Any
from google.adk.tools import ToolContext
from app.firebase_service import firestore_service

logger = logging.getLogger("folk_agents.tools.firebase")


async def save_curriculum_to_firestore(
    package_id: str,
    lesson_data_json: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Persists a synthesized curriculum lesson package into Firebase Firestore.

    Args:
        package_id: Unique ID of the lesson package (e.g. pkg_cell_bio_01).
        lesson_data_json: Serialized JSON string containing the full lesson package assets.

    Returns:
        A dict with status, package_id, and persistence confirmation.
    """
    try:
        data = json.loads(lesson_data_json)
    except Exception:
        data = {"raw_payload": lesson_data_json}

    # Store in session state for fast retrieval
    tool_context.state[f"saved_package_{package_id}"] = data
    tool_context.state["saved_package_id"] = package_id
    tool_context.state["saved_package_data"] = data

    # Persist to Firestore collection
    await firestore_service.save_document("curricula", package_id, data)

    return {
        "status": "success",
        "package_id": package_id,
        "message": f"Successfully persisted curriculum package {package_id} to Firestore.",
    }


async def save_session_evaluation_tool(
    session_id: str,
    student_id: str,
    evaluation_json: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Persists a discrete, immutable session evaluation record into the Firestore 'session_evaluations' collection.

    Args:
        session_id: The unique ID for this learning session.
        student_id: The student ID.
        evaluation_json: Serialized JSON containing comprehension score, friction points, cognitive load, and takeaways.

    Returns:
        Dict confirming persistence of the session evaluation record.
    """
    import datetime

    try:
        eval_data = json.loads(evaluation_json)
    except Exception:
        eval_data = {"raw_evaluation": evaluation_json}

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    timestamp_slug = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    doc_id = f"{session_id}_{timestamp_slug}" if not session_id.endswith(timestamp_slug[:8]) else session_id

    eval_data["session_id"] = doc_id
    eval_data["student_id"] = student_id
    eval_data["evaluated_at"] = now_iso

    # Save to session state
    tool_context.state["session_evaluation"] = eval_data

    # Persist as an individual lesson sitting document in Firestore
    await firestore_service.save_document("session_evaluations", doc_id, eval_data)

    return {
        "status": "success",
        "session_id": doc_id,
        "collection": "session_evaluations",
        "message": f"Saved discrete session evaluation {doc_id} to Firestore.",
    }



async def fetch_student_profile(
    student_id: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Fetches the longitudinal cognitive and learning profile of a student.

    Args:
        student_id: Unique identifier for the student.

    Returns:
        A dict containing the student's mastery map, reading level, misconceptions, and affinities.
    """
    # Check if cached in user-scoped ADK state
    user_state_key = f"user:profile_{student_id}"
    if user_state_key in tool_context.state:
        return {
            "status": "success",
            "source": "adk_user_state",
            "profile": tool_context.state[user_state_key],
        }

    # Otherwise fetch from Firestore
    profile = await firestore_service.get_document("student_profiles", student_id)
    if profile:
        # Cache in ADK user state
        tool_context.state[user_state_key] = profile
        return {"status": "success", "source": "firestore", "profile": profile}

    # Default baseline if new student
    default_profile = {
        "student_id": student_id,
        "reading_level": "Standard Baseline",
        "learning_style_affinities": ["Visual Diagrams", "Real-world Analogies"],
        "mastery_map": {},
        "recurrent_misconceptions": [],
        "cognitive_growth_trend": "New Student",
        "total_sessions_completed": 0,
        "scaffolding_recommendations": ["Start with intuitive diagrams and interactive checkpoints"],
    }
    tool_context.state[user_state_key] = default_profile
    await firestore_service.save_document("student_profiles", student_id, default_profile)
    return {"status": "success", "source": "initialized_default", "profile": default_profile}


async def persist_teacher_approval(
    plan_id: str,
    student_id: str,
    approved: bool,
    teacher_notes: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Persists teacher Human-In-The-Loop (HITL) approval or edits to a remediation plan.

    Args:
        plan_id: Unique identifier of the remediation plan.
        student_id: Student ID targeted by this remediation plan.
        approved: True if approved, False if rejected or deferred.
        teacher_notes: Notes and guidance from the teacher.

    Returns:
        Confirmation dict with timestamp and update status.
    """
    import datetime

    record = {
        "plan_id": plan_id,
        "student_id": student_id,
        "approved": approved,
        "teacher_notes": teacher_notes,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "teacher_approved" if approved else "rejected",
    }

    # Write to ADK state
    tool_context.state[f"remediation_status_{plan_id}"] = record
    tool_context.state[f"user:active_remediations_{student_id}"] = record

    # Persist to Firestore remediation_plans
    await firestore_service.save_document("remediation_plans", plan_id, record)

    # If approved, update student profile in Firestore
    if approved:
        profile = await firestore_service.get_document("student_profiles", student_id) or {}
        recs = profile.get("scaffolding_recommendations", [])
        directive = f"Remediation Plan {plan_id}: {teacher_notes}" if teacher_notes else f"Remediation Plan {plan_id} approved"
        if directive not in recs:
            recs.append(directive)
        profile["scaffolding_recommendations"] = recs
        await firestore_service.save_document("student_profiles", student_id, profile)

    return {
        "status": "success",
        "plan_id": plan_id,
        "persisted_state": record["status"],
        "message": f"Remediation plan {plan_id} for student {student_id} set to {record['status']} and synced to student profile.",
    }


async def load_curriculum_package(
    package_id: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Loads an existing curriculum lesson package (text, diagrams, quizzes) from Firestore or session cache.

    Args:
        package_id: Unique identifier of the lesson package (e.g. pkg_cell_bio_01).

    Returns:
        Dict with status and complete curriculum assets for student delivery.
    """
    if f"saved_package_{package_id}" in tool_context.state:
        pkg = tool_context.state[f"saved_package_{package_id}"]
        tool_context.state["active_lesson_package"] = pkg
        return {"status": "success", "source": "session_state", "package_id": package_id, "package": pkg}

    pkg = await firestore_service.get_document("curricula", package_id)
    if pkg:
        tool_context.state[f"saved_package_{package_id}"] = pkg
        tool_context.state["active_lesson_package"] = pkg
        return {"status": "success", "source": "firestore", "package_id": package_id, "package": pkg}

    return {"status": "not_found", "message": f"Curriculum package {package_id} not found in Firestore."}


async def list_available_curricula(
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Lists all available curriculum packages currently stored in Firestore.

    Returns:
        Dict with count and list of available packages with titles and IDs.
    """
    all_packages = await firestore_service.list_collection("curricula")
    summary = []
    for pkg_id, data in all_packages.items():
        title = "Untitled Lesson"
        if isinstance(data, dict):
            if "primary_text" in data and isinstance(data["primary_text"], dict):
                title = data["primary_text"].get("lesson_title", title)
            elif "framework" in data and isinstance(data["framework"], dict):
                title = data["framework"].get("topic", title)
        summary.append({"package_id": pkg_id, "title": title})

    return {"status": "success", "total_packages": len(summary), "curricula": summary}

