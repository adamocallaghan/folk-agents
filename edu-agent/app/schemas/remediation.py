from __future__ import annotations

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class InterventionRule(BaseModel):
    rule_id: str
    target_concept: str
    action_type: Literal["add_analogy", "lower_lexile", "insert_visual_scaffold", "pace_reduction", "pre_quiz_primer"]
    description: str
    rationale_from_profile: str


class RemediationPlan(BaseModel):
    plan_id: str
    student_id: str
    created_at: str
    identified_learning_gaps: List[str]
    proposed_interventions: List[InterventionRule]
    expected_outcome: str
    status: Literal["proposed", "teacher_approved", "rejected", "applied"] = "proposed"
    teacher_notes: Optional[str] = None
    approval_timestamp: Optional[str] = None


class TeacherApprovalRequest(BaseModel):
    plan_id: str
    student_id: str
    approved: bool
    teacher_id: str
    teacher_comments: Optional[str] = None
    custom_rule_overrides: Optional[List[InterventionRule]] = None
