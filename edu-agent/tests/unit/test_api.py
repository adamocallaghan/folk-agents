import pytest
from fastapi.testclient import TestClient
from app.fast_api_app import app

client = TestClient(app)


def test_api_health():
    """Verify health endpoint returns active workflows and system metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Workflow 1: Curriculum Generation & Structuring" in data["workflows"]
    assert "Workflow 2: Student Interactive Delivery & Chat" in data["workflows"]
    assert "Workflow 3: Analytics & Longitudinal Memory" in data["workflows"]
    assert "Workflow 4: Teacher Review & HITL Governance" in data["workflows"]


def test_get_student_profile_default():
    """Verify retrieval of seeded student profile."""
    response = client.get("/api/student/profile/student_demo_101")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["profile"]["student_id"] == "student_demo_101"
    assert "Visual Diagrams" in data["profile"]["learning_style_affinities"]


def test_teacher_approval_hitl_endpoint():
    """Verify Human-In-The-Loop teacher approval endpoint and Firestore persistence."""
    payload = {
        "plan_id": "plan_test_999",
        "student_id": "student_demo_101",
        "approved": True,
        "teacher_id": "teacher_alex",
        "teacher_comments": "Approved. Provide extra Mermaid diagrams on chloroplasts.",
        "custom_rule_overrides": [
            {
                "rule_id": "rule_01",
                "target_concept": "Photosynthesis - Light Reaction",
                "action_type": "insert_visual_scaffold",
                "description": "Show visual flowchart before quiz",
                "rationale_from_profile": "Student affinity is visual",
            }
        ],
    }
    response = client.post("/api/teacher/approve-remediation", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["approved"] is True

    # Verify student profile was updated with teacher directive
    prof_resp = client.get("/api/student/profile/student_demo_101")
    assert prof_resp.status_code == 200
    prof_data = prof_resp.json()
    recs = prof_data["profile"]["scaffolding_recommendations"]
    assert any("Provide extra Mermaid diagrams" in r for r in recs)
