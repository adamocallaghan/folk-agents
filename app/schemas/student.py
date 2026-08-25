from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StudentAnswer(BaseModel):
    question_id: str
    selected_answer: str
    is_correct: bool
    time_taken_seconds: Optional[int] = None
    attempt_count: int = 1


class QuizSubmission(BaseModel):
    session_id: str
    student_id: str
    package_id: str
    answers: List[StudentAnswer]
    total_score_percentage: float
    submitted_at: str


class ChatMessageRecord(BaseModel):
    role: str = Field(description="'user' (student) or 'assistant' (agent)")
    content: str
    timestamp: str
    topic_context: Optional[str] = None


class ChatFeedbackLog(BaseModel):
    session_id: str
    student_id: str
    messages: List[ChatMessageRecord]
    identified_confusions: List[str] = Field(default_factory=list)
    engagement_rating: Optional[str] = None


class SessionEvaluation(BaseModel):
    session_id: str
    student_id: str
    lesson_id: str
    comprehension_score: float = Field(description="Normalized 0.0-100.0 score")
    friction_points: List[str] = Field(description="Specific concepts where student hesitated or failed")
    cognitive_load_index: str = Field(description="Low / Optimal / High / Overloaded")
    active_inquiry_level: str = Field(description="Passive / Moderate / Highly Curious")
    immediate_takeaways: List[str] = Field(description="Key takeaways from this ephemeral session")


class ConceptMastery(BaseModel):
    concept_name: str
    mastery_percentage: float = Field(ge=0.0, le=100.0)
    attempts: int = 0
    last_tested_date: str = ""
    status: str = Field(default="in_progress", description="unexplored / in_progress / mastered / needs_remediation")


class LearningModalities(BaseModel):
    preferred_pacing: str = Field(default="Chunked Step-by-Step", description="e.g. Chunked Step-by-Step / Fast-Paced Exploratory / Spiral Review")
    primary_modalities: List[str] = Field(default_factory=lambda: ["Visual Diagrams", "Real-World Analogies"], description="e.g. ['Visual-Kinesthetic', 'Concrete Analogies', 'Dual-Coding']")
    symbolic_reasoning_comfort: str = Field(default="Developing", description="e.g. High / Developing / Needs Concrete Scaffolding")
    inquiry_disposition: str = Field(default="Inquisitive", description="e.g. Highly Inquisitive & Hypothesis-Driven / Cautious & Verification-Seeking / Passive")


class LongitudinalProfile(BaseModel):
    student_id: str
    reading_level: str = "Grade Level Baseline"
    learning_style_affinities: List[str] = Field(default_factory=list, description="e.g. ['Visual Diagrams', 'Audio Walkthroughs', 'Analogies']")
    learning_modalities: LearningModalities = Field(default_factory=LearningModalities)
    mastery_map: Dict[str, ConceptMastery] = Field(default_factory=dict)
    recurrent_misconceptions: List[str] = Field(default_factory=list)
    conceptual_bottlenecks: List[str] = Field(default_factory=list, description="Cross-topic meta-cognitive bottlenecks (e.g. 'Struggles bridging microscopic causes to macroscopic outcomes')")
    cross_topic_patterns: List[str] = Field(default_factory=list, description="High-level cognitive patterns observed across multiple subjects/domains")
    cognitive_growth_trend: str = "Steady Progression"
    total_sessions_completed: int = 0
    scaffolding_recommendations: List[str] = Field(default_factory=list)
    teacher_macro_guidance: List[str] = Field(default_factory=list, description="Strategic pedagogical guidance for teachers during instruction and class planning")
    last_updated: str = ""

