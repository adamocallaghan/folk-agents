# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import os
import uuid
import datetime
from collections.abc import AsyncIterator
from typing import Dict, Any, Optional, List

from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.genai import types

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.firebase_service import firestore_service
from app.schemas.curriculum import LessonPackage
from app.schemas.student import SessionEvaluation, LongitudinalProfile
from app.schemas.remediation import RemediationPlan, TeacherApprovalRequest

load_dotenv()
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ and not os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "*").split(",") if os.getenv("ALLOW_ORIGINS") else ["*"]
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ============================================================================
# API Request & Response Schemas for Next.js Frontend
# ============================================================================
class CurriculumGenerateRequest(BaseModel):
    teacher_input: str = Field(description="Raw notes or syllabus outline from teacher")
    target_age_group: str = Field(default="Grade 7-8 (12-14yo)", description="Target age/grade")
    enable_audio: bool = Field(default=True, description="Whether to generate TTS audio script")
    enable_simplification: bool = Field(default=False, description="Generate lower Lexile variation")
    package_id: Optional[str] = None


class StudentChatRequest(BaseModel):
    student_id: str
    session_id: str
    message: str
    lesson_id: Optional[str] = None


class SessionEvaluationRequest(BaseModel):
    session_id: str
    student_id: str
    lesson_id: str
    quiz_answers: Dict[str, Any] = Field(default_factory=dict)
    session_confusions: List[Dict[str, Any]] = Field(default_factory=list)
    chat_transcript: str = ""


class TeacherDiscoveryRequest(BaseModel):
    teacher_id: str
    student_id: str
    message: str
    session_id: Optional[str] = None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name

    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


otel_to_cloud = os.getenv("OTEL_TO_CLOUD", "false").lower() in ("true", "1")

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=otel_to_cloud,
    lifespan=lifespan,
)
app.title = "Folk Multi-Agent Platform"
app.description = "ADK-powered Folk Multi-Agent Education System: Curriculum Generation, Socratic Delivery, Longitudinal Memory, and Teacher HITL Governance."


# ============================================================================
# Dedicated REST Endpoints for Next.js & Frontend Integrations
# ============================================================================

@app.get("/api/health")
async def health_check():
    """System health and active workflow status."""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "workflows": [
            "Workflow 1: Curriculum Generation & Structuring",
            "Workflow 2: Student Interactive Delivery & Chat",
            "Workflow 3: Analytics & Longitudinal Memory",
            "Workflow 4: Teacher Review & HITL Governance",
        ],
        "framework": "Google Agent Development Kit (ADK)",
        "model": os.getenv("GEMINI_MODEL", "gemini-3.7-flash"),
    }


@app.post("/api/curriculum/generate")
async def generate_curriculum(req: CurriculumGenerateRequest):
    """Workflow 1: Generates a complete multi-modal curriculum package (Framework, Text, Diagrams, Quiz, Audio)."""
    pkg_id = req.package_id or f"pkg_{uuid.uuid4().hex[:8]}"
    session_id = f"sess_curriculum_{pkg_id}"
    user_id = "teacher_admin"

    session_service = services.get_session_service()
    
    # Initialize session state with parameters
    initial_state = {
        "teacher_input": req.teacher_input,
        "target_age_group": req.target_age_group,
        "enable_audio": req.enable_audio,
        "enable_simplification": req.enable_simplification,
        "package_id": pkg_id,
    }

    try:
        session = await session_service.get_session(
            app_name=app.state.agent_app_name,
            session_id=session_id,
            user_id=user_id,
        )
        if not session:
            session = await session_service.create_session(
                app_name=app.state.agent_app_name,
                session_id=session_id,
                user_id=user_id,
                state=initial_state,
            )
        else:
            session.state.update(initial_state)

        # Run the curriculum generation workflow
        from app.workflows.workflow1_curriculum import curriculum_generation_workflow

        runner: Runner = app.state.runner
        events_output = []
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"Generate full curriculum for: {req.teacher_input} (Age: {req.target_age_group})")],
        )

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message,
        ):
            events_output.append(event)

        # Retrieve resulting assets from state or Firestore
        saved = await firestore_service.get_document("curricula", pkg_id)
        if not saved:
            # Fallback compile from session state
            saved = {
                "package_id": pkg_id,
                "framework": session.state.get("lesson_framework", {}),
                "primary_text": session.state.get("primary_text", {}),
                "visuals": session.state.get("visual_assets", {}),
                "assessment": session.state.get("assessment_package", {}),
                "audio": session.state.get("audio_package", {}),
                "simplified_variation": session.state.get("simplified_variation"),
            }
            await firestore_service.save_document("curricula", pkg_id, saved)

        return {
            "status": "success",
            "package_id": pkg_id,
            "curriculum": saved,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Curriculum generation failed: {str(e)}")


@app.post("/api/student/chat")
async def student_chat(req: StudentChatRequest):
    """Workflow 2: Interactive Socratic delivery, quiz responses, and student confusion tracking."""
    session_service = services.get_session_service()
    
    # Fetch or initialize student profile
    user_state_key = f"user:profile_{req.student_id}"
    profile = await firestore_service.get_document("student_profiles", req.student_id)

    session = await session_service.get_session(
        app_name=app.state.agent_app_name,
        session_id=req.session_id,
        user_id=req.student_id,
    )
    if not session:
        session = await session_service.create_session(
            app_name=app.state.agent_app_name,
            session_id=req.session_id,
            user_id=req.student_id,
            state={
                "student_id": req.student_id,
                "lesson_id": req.lesson_id or "default_lesson",
                user_state_key: profile or {},
                "session_confusions": [],
                "quiz_answers": {},
            },
        )

    runner: Runner = app.state.runner
    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=req.message)],
    )

    responses = []
    async for event in runner.run_async(
        user_id=req.student_id,
        session_id=req.session_id,
        new_message=user_content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    responses.append(part.text)

    # Refresh session state
    session = await session_service.get_session(
        app_name=app.state.agent_app_name,
        session_id=req.session_id,
        user_id=req.student_id,
    )

    return {
        "status": "success",
        "student_id": req.student_id,
        "session_id": req.session_id,
        "reply": "\n".join(responses) if responses else "Response received.",
        "confusions_logged": session.state.get("session_confusions", []) if session else [],
        "quiz_state": session.state.get("quiz_answers", {}) if session else {},
    }


@app.post("/api/analytics/evaluate-session")
async def evaluate_session(req: SessionEvaluationRequest):
    """Workflow 3: Evaluates ephemeral session results and updates long-term student memory."""
    session_id = f"eval_{req.session_id}"
    session_service = services.get_session_service()

    state_init = {
        "session_id": req.session_id,
        "student_id": req.student_id,
        "lesson_id": req.lesson_id,
        "quiz_answers": req.quiz_answers,
        "session_confusions": req.session_confusions,
        "chat_transcript": req.chat_transcript,
    }

    session = await session_service.create_session(
        app_name=app.state.agent_app_name,
        session_id=session_id,
        user_id=req.student_id,
        state=state_init,
    )

    runner: Runner = app.state.runner
    prompt = types.Content(
        role="user",
        parts=[types.Part.from_text(text=f"Evaluate learning session {req.session_id} for student {req.student_id}")],
    )

    async for _ in runner.run_async(
        user_id=req.student_id,
        session_id=session_id,
        new_message=prompt,
    ):
        pass

    # Retrieve evaluated short-term result and updated longitudinal profile
    updated_profile = await firestore_service.get_document("student_profiles", req.student_id)
    eval_result = session.state.get("session_evaluation", {})

    return {
        "status": "success",
        "session_id": req.session_id,
        "student_id": req.student_id,
        "session_evaluation": eval_result,
        "updated_longitudinal_profile": updated_profile,
    }


@app.post("/api/teacher/discovery")
async def teacher_discovery(req: TeacherDiscoveryRequest):
    """Workflow 4: Multi-turn discovery dialogue between educator and AI copilot."""
    session_id = req.session_id or f"teacher_disc_{req.student_id}"
    session_service = services.get_session_service()

    profile = await firestore_service.get_document("student_profiles", req.student_id)
    
    session = await session_service.get_session(
        app_name=app.state.agent_app_name,
        session_id=session_id,
        user_id=req.teacher_id,
    )
    if not session:
        session = await session_service.create_session(
            app_name=app.state.agent_app_name,
            session_id=session_id,
            user_id=req.teacher_id,
            state={
                "student_id": req.student_id,
                "student_profile": profile or {},
                "active_remediations": [],
            },
        )

    runner: Runner = app.state.runner
    user_msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=req.message)],
    )

    responses = []
    async for event in runner.run_async(
        user_id=req.teacher_id,
        session_id=session_id,
        new_message=user_msg,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    responses.append(part.text)

    return {
        "status": "success",
        "teacher_id": req.teacher_id,
        "student_id": req.student_id,
        "session_id": session_id,
        "reply": "\n".join(responses) if responses else "Understood.",
    }


@app.post("/api/teacher/approve-remediation")
async def approve_remediation(req: TeacherApprovalRequest):
    """Workflow 4 (HITL Gate): Explicit teacher approval/rejection of remediation plan with Firestore persistence."""
    import datetime

    record = {
        "plan_id": req.plan_id,
        "student_id": req.student_id,
        "approved": req.approved,
        "teacher_id": req.teacher_id,
        "teacher_notes": req.teacher_comments or "",
        "custom_rule_overrides": [r.model_dump() for r in req.custom_rule_overrides] if req.custom_rule_overrides else [],
        "approval_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "teacher_approved" if req.approved else "rejected",
    }

    # Persist to Firestore
    await firestore_service.save_document("remediation_plans", req.plan_id, record)

    # If approved, update student active remediations
    if req.approved:
        profile = await firestore_service.get_document("student_profiles", req.student_id) or {}
        recs = profile.get("scaffolding_recommendations", [])
        if req.teacher_comments:
            recs.append(f"Teacher directive: {req.teacher_comments}")
        profile["scaffolding_recommendations"] = recs
        await firestore_service.save_document("student_profiles", req.student_id, profile)

    return {
        "status": "success",
        "plan_id": req.plan_id,
        "approved": req.approved,
        "message": f"Remediation plan {req.plan_id} successfully persisted with status: {record['status']}",
    }


@app.get("/api/student/profile/{student_id}")
async def get_student_profile(student_id: str):
    """Retrieves longitudinal student cognitive profile from Firestore / user memory."""
    profile = await firestore_service.get_document("student_profiles", student_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Student profile {student_id} not found.")
    return {"status": "success", "student_id": student_id, "profile": profile}


@app.get("/api/curriculum/{package_id}")
async def get_curriculum_package(package_id: str):
    """Retrieves stored curriculum package from Firestore."""
    pkg = await firestore_service.get_document("curricula", package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Curriculum package {package_id} not found.")
    return {"status": "success", "package_id": package_id, "curriculum": pkg}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
