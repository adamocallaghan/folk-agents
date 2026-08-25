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
You are the Master Education System Coordinator (OmniEdu Hub).
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

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=root_instruction,
    description="Master Education System Coordinator orchestrating curriculum generation, student delivery, analytics memory, and teacher HITL governance.",
    sub_agents=[
        curriculum_generation_workflow,
        student_delivery_agent,
        analytics_and_memory_workflow,
        teacher_discovery_agent,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
