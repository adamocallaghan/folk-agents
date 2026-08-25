from __future__ import annotations

import json
import uuid
import datetime
from typing import AsyncGenerator, Dict, Any, Optional

from google.adk.agents import Agent, SequentialAgent, ParallelAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.models import Gemini
from google.genai import types

from app.schemas.curriculum import (
    LessonFramework,
    PrimaryLessonText,
    VisualAssetsPackage,
    AssessmentPackage,
    AudioPackage,
    SimplifiedVariation,
    LessonPackage,
)
from app.tools.firebase_tools import save_curriculum_to_firestore
from app.tools.curriculum_tools import validate_mermaid_syntax, estimate_reading_level

MODEL = "gemini-3.7-flash"

# ============================================================================
# 1. Root Framework Coordinator Agent
# ============================================================================
framework_instruction = """
You are the Lead Curriculum Architect.
Your role is to ingest the teacher's raw notes, curriculum syllabus, and target age group to produce a pedagogical, coherent macro lesson framework.

Analyze the input and generate a structured lesson blueprint:
- A compelling real-world pedagogical hook
- Prerequisites and foundational concepts
- Sequenced lesson outline sections with estimated timings and key learning objectives

Target Age Group: {target_age_group}
Raw Notes / Syllabus input: {teacher_input}
"""

framework_agent = Agent(
    name="framework_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=framework_instruction,
    description="Builds the macro pedagogical lesson structure from teacher syllabus and notes.",
    output_schema=LessonFramework,
    output_key="lesson_framework",
)


# ============================================================================
# 2. Text Synthesizer Agent
# ============================================================================
text_instruction = """
You are the Master Educational Content Author.
Your role is to synthesize engaging, high-quality primary lesson text based strictly on the approved lesson framework.

Framework:
{lesson_framework}

Target Age & Reading Level: {target_age_group}

Guidelines:
- Match vocabulary and sentence complexity to the target age group.
- Provide vivid explanations, relatable analogies, clear section headings, and structured Markdown formatting.
- Include 'callout_box' elements with mnemonic aids or fun facts.
- Include a concluding summary and a comprehensive glossary of terms.
"""

text_agent = Agent(
    name="text_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=text_instruction,
    description="Synthesizes the core textbook/lesson content tailored to reading levels.",
    output_schema=PrimaryLessonText,
    output_key="primary_text",
)


# ============================================================================
# 3. Parallel Fan-Out: Diagram Agent & Assessment Agent
# ============================================================================
diagram_instruction = """
You are an Educational Visual Architect and Mermaid.js diagram expert.
Your job is to generate clear, valid Mermaid.js diagrams (flowcharts, sequence diagrams, mindmaps, or cycle diagrams) that visually represent key concepts in the lesson.

Lesson Content:
{primary_text}

Rules:
- Generate 1 to 3 distinct visual diagrams that reinforce the lesson concepts.
- Use valid Mermaid syntax (e.g. `flowchart TD`, `mindmap`, `sequenceDiagram`).
- Provide an educational caption explaining how to interpret each diagram.
"""

diagram_agent = Agent(
    name="diagram_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=diagram_instruction,
    description="Generates educational Mermaid.js diagrams to visually reinforce lesson concepts.",
    output_schema=VisualAssetsPackage,
    output_key="visual_assets",
)

quiz_instruction = """
You are an Assessment & Diagnostic Specialist.
Your job is to design a balanced, multi-format validation quiz based on the lesson text to assess student mastery.

Lesson Content:
{primary_text}

Rules:
- Generate 4 to 6 diverse questions across types: multiple_choice, concept_check, true_false, and short_answer.
- For each question provide:
  * Clear prompt
  * Plausible options (for multiple choice)
  * The exact correct answer
  * A clear explanation of why it is correct
  * A gentle, Socratic hint that encourages critical thinking without giving away the answer directly.
- Set a reasonable passing score percentage (e.g. 70-80).
"""

quiz_agent = Agent(
    name="quiz_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=quiz_instruction,
    description="Generates multi-format quizzes with Socratic hints and diagnostic explanations.",
    output_schema=AssessmentPackage,
    output_key="assessment_package",
)

# Parallel Fan-Out
parallel_asset_generator = ParallelAgent(
    name="parallel_asset_generator",
    sub_agents=[diagram_agent, quiz_agent],
    description="Concurrently produces visual blueprints and multi-format quizzes.",
)


# ============================================================================
# 4. Dynamic Conditional Routing Layer: Audio Agent & Simplification Agent
# ============================================================================
audio_instruction = """
You are an Audio Learning Specialist and Educational Podcaster.
Your role is to transform the lesson text into an audio script suitable for Text-to-Speech (TTS) narration or podcast-style delivery.

Lesson Content:
{primary_text}

Guidelines:
- Write lively, conversational spoken segments with natural pacing cues.
- Include SSML markup when helpful (e.g. `<break time="500ms"/>`, `<emphasis level="moderate">`).
- Keep segments structured and engaging for auditory learners.
"""

audio_agent = Agent(
    name="audio_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=audio_instruction,
    description="Generates audio scripts and SSML cues for auditory learners.",
    output_schema=AudioPackage,
    output_key="audio_package",
)

simplification_instruction = """
You are an Inclusive Education & Accessibility Specialist.
Your job is to adapt the lesson for students requiring reading level accommodations, ESL/ELL support, or lower Lexile levels.

Original Lesson:
{primary_text}

Rules:
- Simplify vocabulary and shorten sentence structures while maintaining conceptual rigor.
- Provide explicit vocabulary scaffolding with simplified definitions.
- Retain all core concepts without dumbing down the scientific/historical truth.
"""

simplification_agent = Agent(
    name="simplification_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=simplification_instruction,
    description="Produces simplified variations and vocabulary scaffolding for reading accommodations.",
    output_schema=SimplifiedVariation,
    output_key="simplified_variation",
)


class DynamicConditionalEnhancer(BaseAgent):
    """Dynamically routes execution to audio or simplification sub-agents based on session flags."""

    def __init__(
        self,
        name: str = "conditional_enhancer",
        audio_sub_agent: Agent = audio_agent,
        simplification_sub_agent: Agent = simplification_agent,
    ):
        super().__init__(
            name=name,
            sub_agents=[audio_sub_agent, simplification_sub_agent],
            description="Conditionally invokes audio synthesis or text simplification based on runtime parameters.",
        )
        self.audio_sub_agent = audio_sub_agent
        self.simplification_sub_agent = simplification_sub_agent

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        enable_audio = ctx.session.state.get("enable_audio", False)
        modalities = ctx.session.state.get("modalities", [])
        if isinstance(modalities, list) and "audio" in modalities:
            enable_audio = True

        enable_simplification = ctx.session.state.get("enable_simplification", False)
        student_profile = ctx.session.state.get("student_profile", {})
        if student_profile and "reading_level" in str(student_profile).lower():
            if "accommodat" in str(student_profile).lower() or "below" in str(student_profile).lower():
                enable_simplification = True

        # Run Audio Sub-agent if requested
        if enable_audio:
            async for event in self.audio_sub_agent.run_async(ctx):
                yield event
        else:
            # Provide empty placeholder in state
            ctx.session.state["audio_package"] = {"audio_enabled": False, "segments": []}

        # Run Simplification Sub-agent if requested
        if enable_simplification:
            async for event in self.simplification_sub_agent.run_async(ctx):
                yield event
        else:
            ctx.session.state["simplified_variation"] = None


conditional_enhancer = DynamicConditionalEnhancer()


# ============================================================================
# 5. Synthesizer & Persistence Agent
# ============================================================================
synthesizer_instruction = """
You are the Packaging & Persistence Agent.
Your job is to bundle the framework, primary text, visual assets, assessment quiz, audio, and simplified variations into a consolidated lesson package and persist it.

Use the `save_curriculum_to_firestore` tool to store the final JSON package.

Current Assets in State:
- Framework: {lesson_framework}
- Primary Text: {primary_text}
- Visual Assets: {visual_assets}
- Assessment: {assessment_package}
- Audio Package: {audio_package}
- Simplified Variation: {simplified_variation}
"""

synthesizer_agent = Agent(
    name="synthesizer_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=synthesizer_instruction,
    description="Assembles all lesson modalities into a finalized JSON package and saves to Firestore.",
    tools=[save_curriculum_to_firestore, validate_mermaid_syntax, estimate_reading_level],
    output_key="synthesizer_result",
)


# ============================================================================
# Full Workflow 1 Pipeline
# ============================================================================
curriculum_generation_workflow = SequentialAgent(
    name="curriculum_generation_workflow",
    description="End-to-end curriculum generation pipeline: Framework -> Text -> Parallel Assets -> Conditional Enhancements -> Synthesizer.",
    sub_agents=[
        framework_agent,
        text_agent,
        parallel_asset_generator,
        conditional_enhancer,
        synthesizer_agent,
    ],
)
