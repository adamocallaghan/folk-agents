from __future__ import annotations

import json
from typing import Dict, Any
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.genai import types

from app.tools.firebase_tools import fetch_student_profile

MODEL = "gemini-3.7-flash"


def record_student_confusion(
    concept: str,
    confusion_details: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Records an explicit point of confusion or struggle expressed by the student during chat.

    Args:
        concept: The specific topic or concept (e.g., 'Calvin Cycle', 'ATP vs ADP').
        confusion_details: Description of what the student found difficult or counter-intuitive.

    Returns:
        Confirmation dict with logged confusion item.
    """
    confusions = tool_context.state.get("session_confusions", [])
    entry = {"concept": concept, "details": confusion_details}
    confusions.append(entry)
    tool_context.state["session_confusions"] = confusions

    return {
        "status": "recorded",
        "concept": concept,
        "total_session_confusions": len(confusions),
    }


def record_quiz_answer(
    question_id: str,
    student_answer: str,
    is_correct: bool,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Logs a student's answer attempt for a quiz question during interactive delivery.

    Args:
        question_id: Identifier of the question being answered.
        student_answer: The answer choice or text provided by the student.
        is_correct: Whether the student's answer was correct.

    Returns:
        Summary of student answers recorded in this session so far.
    """
    answers = tool_context.state.get("quiz_answers", {})
    answers[question_id] = {
        "student_answer": student_answer,
        "is_correct": is_correct,
    }
    tool_context.state["quiz_answers"] = answers

    total = len(answers)
    correct_count = sum(1 for a in answers.values() if a.get("is_correct"))

    return {
        "status": "success",
        "question_id": question_id,
        "score_so_far": f"{correct_count}/{total}",
    }


student_delivery_instruction = """
You are "Aura", an empathetic, highly encouraging, and intelligent Socratic Educational Tutor.

Your mission:
1. **Interactive Lesson Delivery**: Deliver lesson material chunk-by-chunk. Adapt your pacing to how the student is responding.
2. **Interactive Quiz Administration**: Present quiz questions one at a time. If the student answers incorrectly, do not simply give the solution—offer a gentle Socratic hint to prompt them to rethink the core mechanism. Call `record_quiz_answer` when evaluating answers.
3. **Conversational Support & Feedback**: Listen attentively to what the student finds confusing or intimidating. Call `record_student_confusion` whenever you detect a misconception or friction point.
4. **Scaffolding & Personalization**: Use real-world analogies, step-by-step mental models, and intuitive breakdown. Check `{user:profile_{student_id}}` or call `fetch_student_profile` to leverage the student's known strengths and preferred affinities.

Context:
- Current Student ID: {student_id}
- Active Lesson Package: {active_lesson_package}
- Student Reading & Affinity Profile: {student_profile}
"""

student_delivery_agent = Agent(
    name="student_delivery_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=student_delivery_instruction,
    description="Interactive student delivery tutor that explains lesson content, administers quizzes, and provides multi-turn conversational support.",
    tools=[
        fetch_student_profile,
        record_quiz_answer,
        record_student_confusion,
    ],
    output_key="student_delivery_response",
)
