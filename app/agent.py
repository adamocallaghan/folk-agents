# ruff: noqa
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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.workflows.workflow1_curriculum import curriculum_generation_workflow
from app.workflows.workflow2_student_delivery import student_delivery_agent
from app.workflows.workflow3_analytics_memory import analytics_and_memory_workflow
from app.workflows.workflow4_teacher_governance import teacher_discovery_agent

import os

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

root_instruction = """
You are Folk, the Master Education System Coordinator (Folk Education Hub).
You orchestrate a comprehensive multi-agent educational ecosystem spanning 4 core domains:

1. **Curriculum Generation & Structuring (`curriculum_generation_workflow`)**:
   - Ingests teacher syllabi, raw notes, and target age groups.
   - Generates structured frameworks, reading-level aligned text, Mermaid.js diagrams, quizzes, optional audio SSML, and simplified variations.
   - Saves final lesson packages into Firestore.

2. **Student Interactive Delivery & Socratic Tutoring (`student_delivery_agent`)**:
   - Delivers interactive lessons step-by-step.
   - Administers quizzes with Socratic hints.
   - Engages in multi-turn student feedback chat and logs confusion points.

3. **Analytics & Longitudinal Memory (`analytics_and_memory_workflow`)**:
   - Performs short-term ephemeral evaluation of quiz results and chat friction points.
   - Synthesizes evolving longitudinal cognitive profiles across sessions using ADK user-scoped memory and Firestore.

4. **Teacher Review & HITL Governance (`teacher_discovery_agent`)**:
   - Assists educators with multi-turn discovery into student/class trends.
   - Proposes macro-remediation strategies and waits for explicit Human-In-The-Loop (HITL) approval before persisting rules.

Direct incoming queries to the appropriate specialist agent or workflow based on user intent.
"""

def default_state_callback(callback_context, **kwargs):
    state = callback_context.state
    defaults = {
        "target_age_group": "Grade 7-8 (12-14yo)",
        "teacher_input": "Standard curriculum lesson topic",
        "student_id": "student_demo_101",
        "lesson_id": "lesson_bio_01",
        "session_id": "session_live_01",
        "active_lesson_package": "General Lesson Module",
        "student_profile": "Standard baseline profile",
        "active_remediations": "None currently active",
        "quiz_answers": {},
        "session_confusions": [],
        "chat_transcript": "",
        "lesson_framework": "Pending Framework Generation",
        "primary_text": "Pending Primary Text Synthesis",
        "visual_assets": "Pending Visual Blueprint",
        "assessment_package": "Pending Quiz Assessment",
        "audio_package": {"audio_enabled": False, "segments": []},
        "simplified_variation": None,
    }
    for key, value in defaults.items():
        if key not in state or state[key] is None:
            state[key] = value
    return None


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=root_instruction,
    description="Folk Master Education System Coordinator orchestrating curriculum generation, student delivery, analytics memory, and teacher HITL governance.",
    before_agent_callback=default_state_callback,
    sub_agents=[
        curriculum_generation_workflow,
        student_delivery_agent,
        analytics_and_memory_workflow,
        teacher_discovery_agent,
    ],
)

from google.adk.plugins.base_plugin import BasePlugin


class DefaultStatePlugin(BasePlugin):
    """Ensures sensible fallback defaults for state placeholders so agents never error when variables are not yet provided."""

    def __init__(self, name: str = "default_state_plugin"):
        super().__init__(name=name)

    async def before_agent_callback(self, *, callback_context, **kwargs):
        state = callback_context.state
        defaults = {
            "target_age_group": "Grade 7-8 (12-14yo)",
            "teacher_input": "Standard curriculum lesson topic",
            "student_id": "student_demo_101",
            "lesson_id": "lesson_bio_01",
            "session_id": "session_live_01",
            "active_lesson_package": "General Lesson Module",
            "student_profile": "Standard baseline profile",
            "active_remediations": "None currently active",
            "quiz_answers": {},
            "session_confusions": [],
            "chat_transcript": "",
            "lesson_framework": "Pending Framework Generation",
            "primary_text": "Pending Primary Text Synthesis",
            "visual_assets": "Pending Visual Blueprint",
            "assessment_package": "Pending Quiz Assessment",
            "audio_package": {"audio_enabled": False, "segments": []},
            "simplified_variation": None,
        }
        for key, value in defaults.items():
            if key not in state or state[key] is None:
                state[key] = value
        return None


app = App(
    root_agent=root_agent,
    name="app",
    plugins=[DefaultStatePlugin()],
)
