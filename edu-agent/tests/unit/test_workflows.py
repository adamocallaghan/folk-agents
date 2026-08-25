import pytest
from app.schemas.curriculum import (
    LessonFramework,
    LessonOutlineSection,
    PrimaryLessonText,
    SectionContent,
    VisualAssetsPackage,
    AssessmentPackage,
    LessonPackage,
)
from app.schemas.student import (
    StudentAnswer,
    QuizSubmission,
    SessionEvaluation,
    LongitudinalProfile,
)
from app.schemas.remediation import (
    InterventionRule,
    RemediationPlan,
    TeacherApprovalRequest,
)
from app.tools.curriculum_tools import validate_mermaid_syntax, estimate_reading_level
from app.workflows.workflow1_curriculum import (
    curriculum_generation_workflow,
    framework_agent,
    text_agent,
    diagram_agent,
    quiz_agent,
    synthesizer_agent,
)
from app.workflows.workflow2_student_delivery import student_delivery_agent
from app.workflows.workflow3_analytics_memory import (
    analytics_and_memory_workflow,
    lesson_evaluator_agent,
    meta_profile_agent,
)
from app.workflows.workflow4_teacher_governance import teacher_discovery_agent
from app.agent import root_agent, app


def test_schemas_instantiation():
    """Verify that all core Pydantic data schemas instantiate and validate correctly."""
    framework = LessonFramework(
        topic="Photosynthesis & Cellular Energy",
        target_age_group="Grade 7-8 (12-14yo)",
        prerequisites=["Basic cell structure (chloroplasts)", "Molecules (CO2, H2O, O2)"],
        pedagogical_hook="Why do leaves change color, and how do trees build massive trunks out of invisible air?",
        sections=[
            LessonOutlineSection(
                section_id="sec_1",
                title="The Sun's Energy Harvesters: Chloroplasts",
                learning_objectives=["Identify chloroplast organelle", "Explain light-dependent reaction"],
                estimated_minutes=15,
                key_concepts=["Chlorophyll", "Photons", "Thylakoid"],
            )
        ],
        core_summary="Comprehensive introductory unit on plant bioenergetics.",
    )
    assert framework.topic == "Photosynthesis & Cellular Energy"
    assert len(framework.sections) == 1

    profile = LongitudinalProfile(
        student_id="student_123",
        reading_level="Grade 8 Baseline",
        learning_style_affinities=["Visual Diagrams", "Analogies"],
    )
    assert profile.student_id == "student_123"

    approval = TeacherApprovalRequest(
        plan_id="plan_001",
        student_id="student_123",
        approved=True,
        teacher_id="teacher_ms_smith",
        teacher_comments="Approved with visual-first scaffolding.",
    )
    assert approval.approved is True


def test_curriculum_tools():
    """Verify Mermaid validation and reading level estimation tools."""
    valid_mermaid = """
    flowchart TD
        A[Sunlight + CO2 + Water] --> B[Chloroplast Thylakoids]
        B --> C[Light Reactions: ATP + NADPH]
        C --> D[Calvin Cycle: Glucose C6H12O6]
    """
    res = validate_mermaid_syntax(valid_mermaid)
    assert res["is_valid"] is True
    assert res["detected_type"] == "flowchart"

    text_sample = "Plants convert sunlight into chemical energy using chlorophyll inside chloroplasts."
    reading_res = estimate_reading_level(text_sample)
    assert reading_res["word_count"] > 5
    assert "estimated_grade_bracket" in reading_res


def test_agent_hierarchy_and_subagents():
    """Verify that all 4 workflows and root agent are properly registered."""
    assert root_agent.name == "root_agent"
    assert len(root_agent.sub_agents) == 4

    subagent_names = [a.name for a in root_agent.sub_agents]
    assert "curriculum_generation_workflow" in subagent_names
    assert "student_delivery_agent" in subagent_names
    assert "analytics_and_memory_workflow" in subagent_names
    assert "teacher_discovery_agent" in subagent_names

    # Workflow 1 checks
    wf1_names = [a.name for a in curriculum_generation_workflow.sub_agents]
    assert "framework_agent" in wf1_names
    assert "text_agent" in wf1_names
    assert "parallel_asset_generator" in wf1_names
    assert "conditional_enhancer" in wf1_names
    assert "synthesizer_agent" in wf1_names

    # Workflow 3 checks
    wf3_names = [a.name for a in analytics_and_memory_workflow.sub_agents]
    assert "lesson_evaluator_agent" in wf3_names
    assert "meta_profile_agent" in wf3_names

    # Verify App name
    assert app.name == "app"
