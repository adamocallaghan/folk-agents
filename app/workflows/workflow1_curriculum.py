from __future__ import annotations

import json
import uuid
import datetime
from typing import AsyncGenerator, Dict, Any, Optional, List

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
    WorkedExamplesPackage,
    ConceptualAnalogiesPackage,
    LessonPackage,
)
from app.tools.firebase_tools import save_curriculum_to_firestore
from app.tools.curriculum_tools import validate_mermaid_syntax, estimate_reading_level

import os

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

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
Target Student Profile Context & Accommodations:
{student_profile_context}
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
Target Student Profile Context & Accommodations:
{student_profile_context}

Guidelines:
- If a target student profile is provided, tailor vocabulary, reading complexity, and conceptual pacing to their reading level, strengths, and accommodations.
- If the student has reading difficulty flags (e.g. Dyslexia, Needs Chunking), write clean, digestible prose with visual bullet anchors.
- Address any known learning gaps or recurring misconceptions directly within the explanations.
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
Student Context: {student_profile_context}

Rules:
- Generate 1 to 3 distinct visual diagrams that reinforce the lesson concepts.
- If the student is flagged as a Visual Reader or needs Flowchart Scaffolds, generate structured flowcharts and decision maps.
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
Student Context: {student_profile_context}

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
# 4. Specialized Conditional Sub-Agents
# ============================================================================

# 4a. Worked Examples Agent (Triggered by: Needs Extra Worked Examples / Math Friction / Step-by-Step)
worked_examples_instruction = """
You are a Lead Pedagogical Worked-Example & Problem-Solving Specialist.
Your job is to craft clear, step-by-step worked examples and application scenarios based on the lesson text for students needing concrete practice.

Lesson Content:
{primary_text}
Student Accommodations:
{student_profile_context}

Rules:
- Generate 2 to 3 detailed, progressive worked examples that deconstruct abstract concepts into concrete, numbered steps.
- For each step, provide:
  * `step_number` (int)
  * `step_title` (concise action title)
  * `explanation` (how and why this step is solved)
  * `key_insight` (a helpful tip or common misconception to avoid)
- Conclude each example with a `core_takeaway` emphasizing the fundamental intuition.
"""

worked_examples_agent = Agent(
    name="worked_examples_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=worked_examples_instruction,
    description="Synthesizes progressive, step-by-step worked examples and problem walkthroughs.",
    output_schema=WorkedExamplesPackage,
    output_key="worked_examples_package",
)

# 4b. Conceptual Analogies & Thought Experiments Agent (Triggered by: Concrete Analogies / Thought Experiments / Math Friction)
analogy_instruction = """
You are a Master Intuitive Explainer and Thought Experiment Author.
Your job is to ground abstract, difficult, or mathematical concepts in vivid real-world analogies and engaging "What If" thought experiments.

Lesson Content:
{primary_text}
Student Context:
{student_profile_context}

Rules:
- Generate 2 to 3 rich conceptual analogies and thought experiments for the key concepts in this lesson.
- For each item, provide:
  * `concept_name` (the formal concept being explained)
  * `real_world_analogy` (an everyday, tangible metaphor that demystifies the concept)
  * `thought_experiment_prompt` (an immersive scenario starting with "Imagine you are...", putting the student in the driver's seat)
  * `why_it_works` (brief explanation connecting the physical analogy back to the formal science/history)
"""

analogy_agent = Agent(
    name="analogy_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=analogy_instruction,
    description="Synthesizes concrete everyday analogies and immersive thought experiments.",
    output_schema=ConceptualAnalogiesPackage,
    output_key="conceptual_analogies_package",
)

# 4c. Audio SSML Narration Agent
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

# 4d. Accessibility & Dual-Lexile Simplifier Agent
simplification_instruction = """
You are an Inclusive Education & Accessibility Specialist.
Your job is to adapt the lesson for students requiring reading level accommodations, ESL/ELL support, or lower Lexile levels.

Original Lesson:
{primary_text}
Student Accommodations:
{student_profile_context}

Rules:
- Simplify vocabulary and shorten sentence structures while maintaining conceptual rigor.
- Provide explicit vocabulary scaffolding with simplified definitions.
- Retain all core concepts without dumbing down the scientific/historical truth.
- Use clear bullet points and structural spacing.
"""

simplification_agent = Agent(
    name="simplification_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=simplification_instruction,
    description="Produces simplified variations and vocabulary scaffolding for reading accommodations.",
    output_schema=SimplifiedVariation,
    output_key="simplified_variation",
)


# ============================================================================
# 5. Dynamic Conditional Enhancer Router
# ============================================================================
class DynamicConditionalEnhancer(BaseAgent):
    """Dynamically evaluates student accommodation flags and modalities to invoke matching sub-agents."""

    audio_sub_agent: Agent = audio_agent
    simplification_sub_agent: Agent = simplification_agent
    worked_examples_sub_agent: Agent = worked_examples_agent
    analogy_sub_agent: Agent = analogy_agent

    def __init__(
        self,
        name: str = "conditional_enhancer",
        audio_sub_agent: Agent = audio_agent,
        simplification_sub_agent: Agent = simplification_agent,
        worked_examples_sub_agent: Agent = worked_examples_agent,
        analogy_sub_agent: Agent = analogy_agent,
        **kwargs,
    ):
        super().__init__(
            name=name,
            sub_agents=[
                audio_sub_agent,
                simplification_sub_agent,
                worked_examples_sub_agent,
                analogy_sub_agent,
            ],
            description="Conditionally routes execution to specialized sub-agents based on student profile flags.",
            audio_sub_agent=audio_sub_agent,
            simplification_sub_agent=simplification_sub_agent,
            worked_examples_sub_agent=worked_examples_sub_agent,
            analogy_sub_agent=analogy_sub_agent,
            **kwargs,
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Extract flags from state and target_student_profile
        profile = ctx.session.state.get("target_student_profile", {}) or {}
        diff_flags = profile.get("reading_difficulty_flags", []) or []
        modalities = profile.get("modalities_flags", []) or profile.get("learning_style_affinities", []) or []
        all_flags_text = (
            " ".join(diff_flags) + " " + " ".join(modalities) + " " + ctx.session.state.get("student_profile_context", "")
        ).lower()

        # Flag 1: Audio Narration
        enable_audio = ctx.session.state.get("enable_audio", False)
        if "audio" in all_flags_text or "podcast" in all_flags_text:
            enable_audio = True

        # Flag 2: Simplification / Lexile Adaptation
        enable_simplification = ctx.session.state.get("enable_simplification", False)
        if (
            "dyslexia" in all_flags_text
            or "esl" in all_flags_text
            or "chunked" in all_flags_text
            or "lower" in all_flags_text
            or "reading difficulty" in all_flags_text
        ):
            enable_simplification = True

        # Flag 3: Worked Examples / Step-by-Step Practice
        enable_worked_examples = False
        if (
            "worked example" in all_flags_text
            or "math" in all_flags_text
            or "formula friction" in all_flags_text
            or "step-by-step" in all_flags_text
        ):
            enable_worked_examples = True

        # Flag 4: Concrete Analogies & Thought Experiments
        enable_analogies = False
        if (
            "analog" in all_flags_text
            or "thought experiment" in all_flags_text
            or "math" in all_flags_text
            or "conceptual first" in all_flags_text
        ):
            enable_analogies = True

        # Run Worked Examples sub-agent if triggered
        if enable_worked_examples:
            async for event in self.worked_examples_sub_agent.run_async(ctx):
                yield event
        else:
            ctx.session.state["worked_examples_package"] = None

        # Run Analogies sub-agent if triggered
        if enable_analogies:
            async for event in self.analogy_sub_agent.run_async(ctx):
                yield event
        else:
            ctx.session.state["conceptual_analogies_package"] = None

        # Run Simplification sub-agent if triggered
        if enable_simplification:
            async for event in self.simplification_sub_agent.run_async(ctx):
                yield event
        else:
            ctx.session.state["simplified_variation"] = None

        # Run Audio sub-agent if requested
        if enable_audio:
            async for event in self.audio_sub_agent.run_async(ctx):
                yield event
        else:
            ctx.session.state["audio_package"] = {"audio_enabled": False, "segments": []}


conditional_enhancer = DynamicConditionalEnhancer()


# ============================================================================
# 6. Synthesizer & Persistence Agent
# ============================================================================
synthesizer_instruction = """
You are the Packaging & Persistence Agent.
Your job is to consolidate the framework, primary text, visual assets, assessment quiz, audio, worked examples, analogies, and simplified variations into a consolidated lesson package and persist it.

Current Assets in State:
- Framework: {lesson_framework}
- Primary Text: {primary_text}
- Visual Assets: {visual_assets}
- Assessment: {assessment_package}
- Worked Examples: {worked_examples_package}
- Conceptual Analogies: {conceptual_analogies_package}
- Audio Package: {audio_package}
- Simplified Variation: {simplified_variation}
- Target Student Context: {student_profile_context}

Instructions:
- Use the `save_curriculum_to_firestore` tool to store the final JSON package.
- If a package_id is provided ({package_id}), use it or generate a clear semantic identifier (e.g. `pkg_topic_name_g7_8`).
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
    sub_agents=[
        framework_agent,
        text_agent,
        parallel_asset_generator,
        conditional_enhancer,
        synthesizer_agent,
    ],
    description="Complete 5-stage multimodal curriculum synthesis pipeline with dynamic conditional branching.",
)

root_agent = curriculum_generation_workflow
