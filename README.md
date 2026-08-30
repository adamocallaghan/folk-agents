# Folk — Adaptive Multi-Agent Educational Platform

**Folk** is an advanced multi-agent pedagogical platform developed with the **Google Agent Development Kit (ADK)** and Python, orchestrated with **Gemini 3.7 Flash** on **Google Cloud Vertex AI**, and deployed to **Google Cloud Run**.

The system synthesizes rich multi-modal curricula, provides real-time Socratic tutoring, analyzes longitudinal student learning memory, and empowers teachers through human-in-the-loop (HITL) governance and AI-assisted remediation.

---

## 🏛️ System Architecture Overview

```
                                  ┌────────────────────────┐
                                  │   Root Orchestrator    │
                                  │       (Folk Hub)       │
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

---

## 🤖 The 4 Core Agentic Workflows

### 1. Workflow 1: Multimodal Adaptive Curriculum Generation
Synthesizes end-to-end, multi-modal lesson packages with universal classroom adaptation:
- **Lead Framework Architect (`framework_agent`)**: Ingests topic prompts, target grade level, and class roster context to structure syllabus, prerequisites, and macro learning objectives.
- **Master Content Author (`text_agent`)**: Generates primary textbook narratives, section bodies, structured callouts, and vocabulary glossaries.
- **Parallel Visual & Assessment Fan-Out (`parallel_asset_generator`)**:
  - **Diagram Architect (`diagram_agent`)**: Generates Mermaid.js flowcharts and concept blueprints.
  - **Assessment Specialist (`quiz_agent`)**: Generates diagnostic quiz questions with multi-tiered Socratic hints and distractors.
- **Concurrent Adaptive Enhancers (`DynamicConditionalEnhancer`)**:
  - Automatically evaluates student difficulty flags (or whole-classroom roster needs) and executes active sub-agents concurrently via `asyncio.gather`:
    - **Worked Examples Agent (`worked_examples_agent`)**: Progressive step-by-step problem walkthroughs with actionable insights.
    - **Analogy & Intuition Agent (`analogy_agent`)**: Real-world concrete analogies and immersive thought experiments.
    - **Simplification Agent (`simplification_agent`)**: Lower-Lexile chunked text variations for ESL/dyslexic learners.
    - **Audio SSML Agent (`audio_agent`)**: Structured audio scripts with speech pauses and expressive tags.
- **Packaging & Single-Document Persistence (`synthesizer_agent`)**: Deterministically compiles all generated assets from session state and commits a single canonical document to Firestore (`curricula` collection).

### 2. Workflow 2: Socratic Student Delivery & Real-Time Scaffolding
- **Student Delivery & Tutor Agent (`student_delivery_agent` / "Aura")**:
  - Multi-turn conversational Socratic tutor context-aware of the current lesson and student accommodations.
  - Formative quiz interaction, misconception diagnosis, and incremental hints without giving away answers directly.

### 3. Workflow 3: Cognitive Analytics & Longitudinal Memory Synthesis
- **Session Evaluator Agent (`lesson_evaluator_agent`)**:
  - Ephemeral diagnostic agent grading quiz accuracy, cognitive load, inquiry depth, and concept mastery friction.
- **Longitudinal Memory Agent (`meta_profile_agent`)**:
  - Synthesizes session evaluation metrics into the student's persistent cognitive profile in Firestore (`student_profiles` collection), updating mastery maps and recurrent misconceptions.

### 4. Workflow 4: Teacher Governance & HITL Discovery Copilot
- **Teacher Copilot Agent (`teacher_discovery_agent` / "Athena")**:
  - Ingests student longitudinal profiles and past `session_evaluations` records across completed lessons.
  - Engages in professional diagnostic dialogue with educators, identifying cross-topic friction points.
  - **Remediation Staging (`generate_remediation_proposal_tool`)**: Stages concrete intervention proposals (e.g. mandatory visual schemas, Socratic checkpoints).
  - **Human-in-the-Loop Gate (`persist_teacher_approval`)**: Waits for explicit teacher approval or edits before locking new scaffolding directives into the student's Firestore profile.

---

## 📁 Repository Structure

```
folk_agents/
├── app/
│   ├── agent.py                     # Root ADK Orchestrator & App definition
│   ├── fast_api_app.py              # Production FastAPI server & REST API proxy gateway
│   ├── firebase_service.py          # Firestore client (database: folk-agents-store)
│   ├── schemas/                     # Strongly-typed Pydantic data schemas
│   │   ├── curriculum.py            # LessonFramework, Text, Visuals, Quizzes, WorkedExamples, Analogies
│   │   ├── student.py               # QuizSubmissions, SessionEvaluation, LongitudinalProfile
│   │   └── remediation.py           # RemediationPlan, InterventionRule, TeacherApprovalRequest
│   ├── tools/                       # ADK Function Tools
│   │   ├── firebase_tools.py        # Firestore persistence, profile fetch, session save
│   │   └── curriculum_tools.py      # Mermaid validation & Lexile estimation
│   ├── workflows/                   # The 4 Agentic Workflows
│   │   ├── workflow1_curriculum.py  # Sequential + Parallel + Async Enhancers + Persistence
│   │   ├── workflow2_student_delivery.py # Socratic Tutor (Aura)
│   │   ├── workflow3_analytics_memory.py # Evaluator & Longitudinal Memory
│   │   └── workflow4_teacher_governance.py # Teacher Discovery Copilot (Athena) & HITL
│   └── app_utils/                   # Service initialization & A2A protocols
├── tests/
│   └── unit/
│       ├── test_workflows.py        # Schema, tool, and agent hierarchy tests
│       └── test_api.py              # FastAPI REST endpoints & HITL tests
├── Dockerfile                       # Production Cloud Run container build
├── pyproject.toml                   # Project dependencies (ADK, FastAPI, Google GenAI)
└── README.md
```

---

## 🛠️ Development & Tooling

### Prerequisites
- Python 3.12+
- `uv` package manager: `uv tool install google-agents-cli`
- Google Cloud SDK (`gcloud`)

### Quick Start
```bash
# 1. Install dependencies
uv sync

# 2. Configure environment (.env)
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=agent-hackathon-506611
GOOGLE_CLOUD_LOCATION=us-east1
FIRESTORE_DATABASE=folk-agents-store
GEMINI_MODEL=gemini-3.7-flash

# 3. Interactive local testing with ADK Playground
agents-cli playground

# 4. Run automated test suite
uv run pytest tests/unit

# 5. Run FastAPI dev server
uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080 --reload
```

---

## 🌐 API Gateway Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/curriculum/generate` | `POST` | Triggers Workflow 1 multi-agent curriculum generation pipeline |
| `/api/curricula` | `GET` | Lists all generated curriculum packages in Firestore |
| `/api/curriculum/{id}` | `GET` | Retrieves full multimodal lesson package |
| `/api/curriculum/{id}` | `DELETE` | Deletes a curriculum document from Firestore |
| `/api/student/chat` | `POST` | Workflow 2 interactive Socratic tutor dialogue (Aura) |
| `/api/analytics/evaluate-session` | `POST` | Workflow 3 session completion evaluation & memory update |
| `/api/teacher/discovery` | `POST` | Workflow 4 teacher governance discovery dialogue (Athena) |
| `/api/teacher/approve-remediation` | `POST` | Explicit HITL teacher sign-off persisting rules to Firestore |
| `/api/student/profiles` | `GET` | Lists all student profiles in the active classroom roster |
| `/api/student/profile/{id}` | `GET` | Retrieves longitudinal cognitive profile for a student |
| `/api/health` | `GET` | System health check & active service status |

---

## 🚢 Google Cloud Infrastructure & Deployment

- **Agent Service (Cloud Run)**: `folk-agent-workflows` (`us-east1`)
- **Frontend Service (Cloud Run)**: `folk-frontend` (`us-east1`) — Next.js 16 standalone container with local session authentication & reverse proxy.
- **LLM Engine**: Gemini 3.7 Flash on Google Cloud Vertex AI.
- **Database**: Google Cloud Firestore (`folk-agents-store`).

Deploy updates via `agents-cli`:
```bash
agents-cli deploy --project agent-hackathon-506611 --region us-east1 --service-account all-things-agentic@agent-hackathon-506611.iam.gserviceaccount.com
```
