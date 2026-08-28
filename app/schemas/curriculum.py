from __future__ import annotations

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class LessonOutlineSection(BaseModel):
    section_id: str = Field(description="Unique ID for section, e.g., sec_1")
    title: str = Field(description="Section title")
    learning_objectives: List[str] = Field(description="Key takeaways for this section")
    estimated_minutes: int = Field(description="Estimated reading/activity time")
    key_concepts: List[str] = Field(description="Primary vocabulary or conceptual anchors")


class LessonFramework(BaseModel):
    topic: str = Field(description="Core subject topic")
    target_age_group: str = Field(description="Target age group, e.g., 'Grade 6-8 (11-14yo)'")
    prerequisites: List[str] = Field(default_factory=list, description="Assumed student background knowledge")
    pedagogical_hook: str = Field(description="Engaging introductory hook / real-world mystery")
    sections: List[LessonOutlineSection] = Field(description="Ordered lesson sections")
    core_summary: str = Field(description="High level summary of the macro lesson design")


class SectionContent(BaseModel):
    section_id: str
    heading: str
    body_markdown: str = Field(description="Explanatory text formatted in clean Markdown")
    callout_box: Optional[str] = Field(default=None, description="Important tip, fun fact, or memory aid")


class PrimaryLessonText(BaseModel):
    lesson_title: str
    reading_level: str = Field(description="Target Lexile or Grade reading level")
    introduction: str
    sections: List[SectionContent]
    conclusion: str
    glossary: Dict[str, str] = Field(default_factory=dict, description="Term to definition mapping")


class VisualBlueprint(BaseModel):
    diagram_id: str
    title: str
    diagram_type: Literal["mermaid_flowchart", "mermaid_sequence", "mermaid_mindmap", "mermaid_er"] = "mermaid_flowchart"
    mermaid_code: str = Field(description="Valid Mermaid.js graph definition")
    caption: str = Field(description="Educational explanation of what this diagram visually conveys")


class VisualAssetsPackage(BaseModel):
    diagrams: List[VisualBlueprint] = Field(default_factory=list)


class QuizQuestion(BaseModel):
    question_id: str
    question_type: Literal["multiple_choice", "true_false", "concept_check", "short_answer"]
    prompt: str
    options: Optional[List[str]] = Field(default=None, description="Choices for multiple choice questions")
    correct_answer: str = Field(description="The correct answer string or key")
    explanation: str = Field(description="Explanation of why this answer is correct")
    hint: str = Field(description="Socratic hint if student struggles")


class AssessmentPackage(BaseModel):
    quiz_title: str
    passing_score: int = Field(default=70, description="Minimum percentage score")
    questions: List[QuizQuestion] = Field(default_factory=list)


class AudioSegment(BaseModel):
    segment_id: str
    speaker_role: Literal["Narrator", "Host", "Tutor", "Student_Voice"] = "Tutor"
    text: str = Field(description="Spoken text script with natural pacing cues")
    ssml_markup: Optional[str] = Field(default=None, description="SSML format markup for TTS engines")
    duration_seconds_estimate: int = 30


class AudioPackage(BaseModel):
    audio_enabled: bool = False
    episode_title: str = ""
    style: Literal["podcast_dialogue", "lecture_narration", "socratic_walkthrough"] = "lecture_narration"
    segments: List[AudioSegment] = Field(default_factory=list)


class SimplifiedVariation(BaseModel):
    needed_for_reading_level: str
    simplified_introduction: str
    simplified_sections: List[SectionContent]
    vocabulary_scaffolding: Dict[str, str]


class WorkedExampleStep(BaseModel):
    step_number: int
    step_title: str
    explanation: str
    key_insight: Optional[str] = None


class WorkedExampleItem(BaseModel):
    example_id: str
    title: str
    problem_or_scenario: str
    steps: List[WorkedExampleStep]
    core_takeaway: str


class WorkedExamplesPackage(BaseModel):
    examples: List[WorkedExampleItem] = Field(default_factory=list)


class ConceptualAnalogyItem(BaseModel):
    analogy_id: str
    concept_name: str
    real_world_analogy: str
    thought_experiment_prompt: str
    why_it_works: str


class ConceptualAnalogiesPackage(BaseModel):
    analogies: List[ConceptualAnalogyItem] = Field(default_factory=list)


class LessonPackage(BaseModel):
    package_id: str
    created_at: str
    target_age_group: str
    framework: LessonFramework
    primary_text: PrimaryLessonText
    visuals: VisualAssetsPackage
    assessment: AssessmentPackage
    audio: Optional[AudioPackage] = None
    simplified_variation: Optional[SimplifiedVariation] = None
    worked_examples: Optional[List[WorkedExampleItem]] = None
    conceptual_analogies: Optional[List[ConceptualAnalogyItem]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
