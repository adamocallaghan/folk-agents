# Folk Multi-Agent Educational Platform

Comprehensive, state-of-the-art educational multi-agent system built using the **Google Agent Development Kit (ADK)** and Python, adhering to Google `agents-cli` standards.

---

## 🏛️ Architecture & Workflow Overview

```
                                  ┌────────────────────────┐
                                  │   Root Orchestrator    │
                                  │     (Folk Hub)         │
                                  └───────────┬────────────┘
                                              │
          ┌───────────────────────┬───────────┴───────────┬───────────────────────┐
          │                       │                       │                       │
          ▼                       ▼                       ▼                       ▼
   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
   │ Workflow 1  │         │ Workflow 2  │         │ Workflow 3  │         │ Workflow 4  │
   │ Curriculum  │         │   Student   │         │ Analytics & │         │   Teacher   │
   │ Generation  │         │  Delivery   │         │   Memory    │         │ Governance  │
   └─────────────┘         └─────────────┘         └─────────────┘         └─────────────┘
```

### 1. Workflow 1: Teacher Curriculum Generation & Structuring
- **Sequential Step 1 — Framework Agent (`framework_agent`)**: Ingests teacher raw notes, syllabus, and target age group to design a pedagogical lesson framework (`LessonFramework`).
- **Sequential Step 2 — Text Synthesizer Agent (`text_agent`)**: Synthesizes the core lesson text with structured sections, callout boxes, conclusions, and vocabulary glossaries matching the target reading level.
- **Concurrent Step 3 — Parallel Fan-Out (`parallel_asset_generator`)**:
  - **Diagram / Visual Agent (`diagram_agent`)**: Generates structured Mermaid.js visual blueprints (`VisualAssetsPackage`).
  - **Assessment / Quiz Agent (`quiz_agent`)**: Creates multi-format validation quizzes (multiple choice, concept check, short answer) with Socratic hints.
- **Step 4 — Dynamic Conditional Routing Layer (`DynamicConditionalEnhancer`)**:
  - **Conditional Audio Agent (`audio_agent`)**: Generates TTS audio narration scripts with SSML pacing cues when audio modality is selected.
  - **Simplification Sub-Agent (`simplification_agent`)**: Synthesizes scaffolded text variations for students requiring lower Lexile / reading accommodations.
- **Step 5 — Synthesizer & Persistence Agent (`synthesizer_agent`)**: Gathers all multimodal assets into a uniform JSON package (`LessonPackage`) and persists to Firebase Firestore (`save_curriculum_to_firestore`).

### 2. Workflow 2: Student Interactive Delivery
- **Student Delivery & Chat Agent (`student_delivery_agent`)**:
  - Delivers lesson components in digestible chunks.
  - Administers interactive quizzes with Socratic hints (`record_quiz_answer`).
  - Multi-turn conversational tutor mode that diagnoses points of confusion (`record_student_confusion`).

### 3. Workflow 3: Analytics & Longitudinal Memory
- **Lesson-Level Evaluator Agent (`lesson_evaluator_agent`)**: Short-term ephemeral diagnostic agent evaluating comprehension scores, friction points, cognitive load index, and active inquiry level.
- **Meta-Profile Synthesizer Agent (`meta_profile_agent`)**: Cross-session memory agent that reads/writes ADK user-scoped states (`user:profile_{student_id}`, `user:mastery_map`) and persists the evolving cognitive/psychological student profile to Firestore.

### 4. Workflow 4: Teacher Review & HITL Governance
- **Teacher Discovery & Approval Agent (`teacher_discovery_agent`)**:
  - Collaborative partner copilot that reads student longitudinal profiles and engages in multi-turn pedagogical discovery.
  - Drafts actionable remediation strategies (`generate_remediation_proposal_tool`).
  - **Human-In-The-Loop (HITL) Gate**: Waits for explicit teacher confirmation (`persist_teacher_approval`) before updating Firestore rules and student scaffolds.

---

## 📁 Modular Project Layout

```
folk-agents/
├── app/
│   ├── agent.py                     # Root Agent Orchestrator & App definition
│   ├── fast_api_app.py              # Next.js ready FastAPI REST + Streaming Server
│   ├── firebase_service.py          # Firebase Firestore client with resilient in-memory fallback
│   ├── schemas/                     # Strongly-typed Pydantic schemas
│   │   ├── curriculum.py            # LessonFramework, Text, Visuals, Quizzes, Audio
│   │   ├── student.py               # QuizSubmissions, ChatLogs, SessionEvaluation, LongitudinalProfile
│   │   └── remediation.py           # RemediationPlan, InterventionRule, TeacherApprovalRequest
│   ├── tools/                       # ADK Function Tools
│   │   ├── firebase_tools.py        # Firestore persistence & user state tools
│   │   └── curriculum_tools.py      # Mermaid validator & reading level estimator
│   ├── workflows/                   # The 4 Core Workflows
│   │   ├── workflow1_curriculum.py  # Sequential + Parallel + Conditional Router + Synthesizer
│   │   ├── workflow2_student_delivery.py # Socratic Tutor & Feedback Agent
│   │   ├── workflow3_analytics_memory.py # Ephemeral Evaluator & Meta-Profile Synthesizer
│   │   └── workflow4_teacher_governance.py # Teacher Discovery & HITL Approval
│   └── app_utils/                   # Services & A2A protocol routes
├── tests/
│   └── unit/
│       ├── test_workflows.py        # Schema, tool, and agent hierarchy tests
│       └── test_api.py              # FastAPI REST endpoints & HITL tests
├── .env.example                     # Environment configuration template
├── pyproject.toml                   # Project dependencies (ADK, FastAPI, Google GenAI)
└── README.md
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
uv sync
# Or using agents-cli
agents-cli install
```

### 2. Configure Environment (`.env`)
To use Google AI Studio:
```env
GEMINI_API_KEY=your-api-key-here
```
Or for Vertex AI:
```env
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

### 3. Run Tests
```bash
uv run pytest tests/unit
```

### 4. Start Local Development Server & Playground
```bash
# Start ADK Interactive Playground
agents-cli playground

# Or run FastAPI server directly (for Next.js integration)
uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌐 Next.js & Frontend API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/curriculum/generate` | `POST` | Trigger Workflow 1 curriculum generation pipeline (returns full multimodal JSON) |
| `/api/student/chat` | `POST` | Interactive Socratic chat, quiz submission, and confusion tracking |
| `/api/analytics/evaluate-session` | `POST` | Close session: evaluate short-term metrics & update long-term user profile |
| `/api/teacher/discovery` | `POST` | Multi-turn teacher discovery chat & remediation drafting |
| `/api/teacher/approve-remediation`| `POST` | Explicit HITL teacher sign-off to persist remediation to Firestore |
| `/api/student/profile/{student_id}`| `GET` | Retrieve student longitudinal profile & concept mastery map |
| `/api/curriculum/{package_id}` | `GET` | Retrieve persisted curriculum package |
| `/api/health` | `GET` | System health check & active workflow listing |

---

## 🚢 Deployment to Google Cloud Run

Deploy directly using `agents-cli`:
```bash
agents-cli deploy
```
