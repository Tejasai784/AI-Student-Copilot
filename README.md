# Autonomous Student Intelligence Platform (ASIP)
### AI Student Copilot — Production-Ready Autonomous Learning & Exam Preparation System

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Architecture Multi--Agent](https://img.shields.io/badge/architecture-Multi--Agent%20AGI-orange.svg)
![Frontend Streamlit](https://img.shields.io/badge/frontend-Streamlit-red.svg)
![Backend FastAPI](https://img.shields.io/badge/backend-FastAPI-teal.svg)

---

## 📌 Executive Overview

The **Autonomous Student Intelligence Platform (ASIP)** is an enterprise-grade, local-first, multi-agent AI system designed to understand academic goals, ingest course materials (syllabi, lecture notes, textbook chapters, past question papers), decompose objectives into daily timetables, execute tool-augmented research and coding sandboxes, detect knowledge gaps, adapt schedules dynamically, and guide students toward high-confidence exam readiness.

Built across three meticulously verified development phases:
- **Phase 1 (Foundation):** Multi-entity database schema, multi-format document ingestion (PDF, DOCX, TXT, MD, CSV), local TF-IDF & Cosine Similarity vector retrieval engine, and multi-provider AI abstraction (Gemini, OpenAI, Offline Mock).
- **Phase 2 (Multi-Agent Reasoning & Safe Tools):** 8 specialized AI agents coordinated by an AGI Controller, 9 safe and sandboxed tools (strict AST calculator, Python sandbox, semantic search, tabular analyzer, quiz generator, etc.), self-correction critic loop, and database audit logging.
- **Phase 3 (Autonomous Platform & Explainability):** 15-step autonomous exam preparation workflow, dynamic timetable adaptation based on weakness discovery, full explainable execution trace visualization, interactive 13-view Streamlit interface, and comprehensive FastAPI REST API.

---

## 🏗️ High-Level Architecture

```
                                    ┌────────────────────────────────────────────────────────┐
                                    │               STUDENT / CLIENT LAYER                  │
                                    │  Streamlit UI (13 Views)   |   FastAPI REST API Client │
                                    └──────────────────────────┬─────────────────────────────┘
                                                               │
                                                               ▼
                                    ┌────────────────────────────────────────────────────────┐
                                    │                 API & CONTROL LAYER                    │
                                    │    FastAPI Application Routes (/api/v1) & Middleware   │
                                    └──────────────────────────┬─────────────────────────────┘
                                                               │
                                                               ▼
        ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
        │                                  MULTI-AGENT ORCHESTRATION LAYER (AGI Controller)                                │
        │                                                                                                                  │
        │   ┌────────────────────┐     ┌─────────────────────┐     ┌────────────────────┐     ┌────────────────────────┐   │
        │   │   Planner Agent    │     │     Study Agent     │     │    Coding Agent    │     │       Math Agent       │   │
        │   │ (Goal -> Schedule) │     │ (Concept Synthesis) │     │  (AST Sandbox Run) │     │  (Step-by-step Proofs) │   │
        │   └────────────────────┘     └─────────────────────┘     └────────────────────┘     └────────────────────────┘   │
        │   ┌────────────────────┐     ┌─────────────────────┐     ┌────────────────────┐     ┌────────────────────────┐   │
        │   │   Research Agent   │     │     Exam Agent      │     │    Memory Agent    │     │      Critic Agent      │   │
        │   │ (Academic Search)  │     │ (Quizzes & Mocks)   │     │ (Redacted Memory)  │     │ (Self-Correction Loop) │   │
        │   └────────────────────┘     └─────────────────────┘     └────────────────────┘     └────────────────────────┘   │
        └──────────────────────────────────────────────────────┬───────────────────────────────────────────────────────────┘
                                                               │
                                                               ▼
        ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
        │                                        SAFE AUDITED TOOL REGISTRY                                                │
        │                                                                                                                  │
        │   • calculator        • python_sandbox     • document_reader     • semantic_search    • tabular_reader            │
        │   • web_research      • quiz_generator     • report_generator    • task_state_manager                            │
        └──────────────────────────────────────────────────────┬───────────────────────────────────────────────────────────┘
                                                               │
                                                               ▼
        ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
        │                                        STORAGE, RETRIEVAL & AI PROVIDERS                                         │
        │                                                                                                                  │
        │   ┌───────────────────────────┐        ┌───────────────────────────┐        ┌────────────────────────────────┐   │
        │   │     SQLite Database       │        │    Local Vector Store     │        │          AI Providers          │   │
        │   │ (15 Relational Entities)  │        │ (TF-IDF & Embeddings)     │        │ (Gemini, OpenAI, Offline Mock) │   │
        │   └───────────────────────────┘        └───────────────────────────┘        └────────────────────────────────┘   │
        └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Primary Acceptance Test

The platform was built and validated against the primary acceptance test benchmark:

> **Student Prompt:**  
> *"Prepare me for my Python exam in 7 days. I have uploaded my syllabus and previous question papers."*

### Expected System Execution & Outcomes:
1. **Material Ingestion & Grounding:** Inspects uploaded files (`python_syllabus.txt`, `python_past_papers.txt`), indexes content chunks into vector storage, and grounds curriculum requirements.
2. **Goal & Curriculum Decomposition:** Identifies core exam topics (Data Types, Control Flow, Functions, OOP, Exception Handling, File I/O, Advanced Python).
3. **Initial 7-Day Timetable:** Builds a day-by-day balanced study schedule across the available timeframe.
4. **Diagnostic Assessment:** Generates and administers a diagnostic quiz across key syllabus competencies.
5. **Weakness Discovery:** Automatically identifies low-scoring areas (e.g., Object-Oriented Programming & Inheritance).
6. **Dynamic Schedule Adaptation:** Injects high-priority remedial tasks into the timetable, reorganizing subsequent study days.
7. **Targeted Remediation & Re-Testing:** Re-tests the student on weak concepts, recording mastery progression.
8. **Memory Retention:** Stores the student's mastery profile and topic affinities into persistent memory with sensitive token redaction.
9. **Explainable Trace:** Logs every agent call, tool execution duration, input/output payload, and critic evaluation into the database.
10. **Exam Readiness Report:** Exports an interactive Markdown & HTML readiness report with topic-level scores, recommendations, and study advice.

### Verifying the Acceptance Test:
Run the end-to-end verification script:
```bash
python verify_phase3.py
```
Output confirms that all 15 autonomous steps execute successfully with zero errors.

---

## 🛠️ Features Breakdown by Phase

### Phase 1: Foundation
- **Robust Database Engine:** Complete relational schema in SQLAlchemy supporting `User`, `StudentProfile`, `Subject`, `Document`, `Topic`, `StudyPlan`, `Quiz`, `Question`, `Answer`, `ExamAttempt`, `Goal`, `Task`, `AgentRun`, `ToolCall`, `Memory`, `Evaluation`, `ProgressRecord`, and `Embedding`.
- **Universal Document Ingestion:** Production parsers for PDF (pypdf), DOCX (python-docx), TXT, Markdown, and CSV files with automatic deduplication, chunking, and validation.
- **Local TF-IDF Vector Engine:** Cosine similarity retrieval with persistent disk indexing in `data/vector_store/`, completely zero-cost and functional offline without mandatory external vector databases.
- **Provider Abstraction:** Unified `BaseAIProvider` interface powering Google Gemini (`gemini-2.0-flash-lite`), OpenAI (`gpt-4o-mini`), and an intelligent `OfflineMockProvider` for zero-crash offline execution and automated CI/CD testing.

### Phase 2: Multi-Agent Reasoning & Safe Tools
- **8 Domain-Specialized Agents:**
  - `PlannerAgent`: Decomposes academic goals into concrete subtasks with dependencies and daily timetables.
  - `StudyAgent`: Synthesizes complex concepts using retrieved document chunks and structured pedagogic techniques.
  - `CodingAgent`: Writes and tests code samples safely through the Python sandbox.
  - `MathAgent`: Solves equations, derives formulas step-by-step, and verifies algebraic steps using the calculator tool.
  - `ResearchAgent`: Performs academic literature research against verified documentation domains.
  - `ExamAgent`: Generates balanced multiple-choice and open-ended questions with scoring rubrics and feedback.
  - `MemoryAgent`: Stores short-term session context and long-term user memories while scrubbing API keys and secrets.
  - `CriticAgent`: Reviews agent responses for hallucinations, syllabus adherence, formatting, and triggers automatic refinement.
- **9 Sandboxed & Audited Tools:**
  1. `calculator`: Safe AST evaluator for mathematical expressions with zero division handling.
  2. `python_sandbox`: Multi-layer Python execution sandbox with forbidden AST imports (`os`, `sys`, `subprocess`, `shutil`) and execution timeout.
  3. `document_reader`: Inspects uploaded document content by page and chunk index.
  4. `semantic_search`: Performs vector similarity lookups against course materials.
  5. `tabular_reader`: Parses CSV files to generate summary statistics, column types, and data previews.
  6. `web_research`: Retrieves academic references with verifiable domain URLs.
  7. `quiz_generator`: Programmatically generates structured quiz questions and answers.
  8. `report_generator`: Generates comprehensive exam readiness reports in Markdown and standalone HTML.
  9. `task_state_manager`: Manages study goal and subtask progress states.

### Phase 3: Autonomous Platform & Explainability
- **15-Step Autonomous Workflow (`AutonomousWorkflowService`):**
  1. Goal Understanding
  2. Document Inspection
  3. Topic Extraction
  4. Day-by-Day Schedule Formulation
  5. Multi-Agent Task Delegation
  6. Diagnostic Quiz Generation
  7. Quiz Evaluation & Scoring
  8. Weakness Detection & Diagnosis
  9. Dynamic Timetable Adaptation
  10. Remedial Task Insertion
  11. Concept Review & Re-Testing
  12. Re-Assessment & Mastery Update
  13. Long-Term Memory Storage
  14. Comprehensive Readiness Report Generation
  15. Complete Execution Trace Assembly
- **Explainable Multi-Agent Trace:** Full visualization of agent thoughts, tool execution payloads, execution duration, and critic decisions.
- **13 Interactive Streamlit Views:**
  1. **Dashboard:** Daily tasks, streak tracker, readiness KPI cards, quick actions.
  2. **AI Tutor / Chat:** Streaming multi-agent conversation with RAG context grounding.
  3. **My Goals:** Long-term academic targets and 1-click Autonomous Exam Prep launcher.
  4. **Study Planner:** Day-by-day timetable with interactive task completion toggles.
  5. **Uploaded Materials:** Multi-format document uploader with chunking inspector.
  6. **Knowledge Base:** Vector store explorer and semantic search playground.
  7. **Agents & Execution Trace:** Deep inspectability into agent reasoning and tool audit logs.
  8. **Quizzes & Mock Exams:** Practice exams with immediate grading and explanations.
  9. **Progress & Weaknesses:** Interactive Plotly charts showing mastery curves and priority gaps.
  10. **Readiness Reports:** Comprehensive exam readiness reports with Markdown/HTML downloads.
  11. **Student Profile:** Target grade, learning pace, study hours, and academic metadata.
  12. **Subjects & Syllabus:** Course and module catalog management.
  13. **Developer & Diagnostics:** System health, database statistics, vector store metrics, and environment checks.

---

## 📦 Installation & Setup Guide

### 1. Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Git (optional)

### 2. Clone / Open the Workspace
```bash
cd D:\AI_Student_Copilot
```

### 3. Create & Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your preferred LLM provider:
```ini
# Choose 'gemini', 'openai', 'offline', or 'auto'
AI_PROVIDER=auto

# To use Google Gemini (Recommended):
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-lite

# To use OpenAI (Fallback):
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```
*Note: If no API keys are configured, the system automatically runs using the high-fidelity `OfflineMockProvider` for 100% functionality without internet or billing.*

---

## 🏃 Running the Application

### 1. Launch the Streamlit Frontend
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 2. Launch the FastAPI Backend (Concurrent or Headless)
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Docs (Swagger UI): `http://localhost:8000/docs`
- Alternative Docs (ReDoc): `http://localhost:8000/redoc`

---

## 🧪 Testing & Verification Suite

The repository includes a comprehensive, automated test suite covering unit, integration, and end-to-end verification.

### Run All Unit and Integration Tests:
```bash
pytest -v
```
*Result: 29 passed test suites.*

### Run Phase Verification Scripts:
```bash
# Verify Phase 1 (Database, Document Loader, Vector Store, AI Provider)
python verify_phase1.py

# Verify Phase 2 (All 8 Agents, 9 Tools, Critic Loop, Audit Logging)
python verify_phase2.py

# Verify Phase 3 (Complete 15-Step Autonomous Exam Prep Workflow)
python verify_phase3.py
```

---

## 📁 Project Directory Structure

```
d:/AI_Student_Copilot/
├── agents/                       # Specialized AI Agents
│   ├── critic_agent.py           # Self-correction and quality assurance
│   ├── coding_agent.py           # Code generator with sandboxed execution
│   ├── exam_agent.py             # Quiz and mock exam creator
│   ├── math_agent.py             # Equation solver and calculator integration
│   ├── memory_agent.py           # Context and memory retention
│   ├── orchestrator.py           # AGI Controller and multi-agent state machine
│   ├── planner_agent.py          # Goal breakdown and timetable generator
│   ├── research_agent.py         # Academic literature researcher
│   └── study_agent.py            # Concept explanations and notes synthesis
├── backend/                      # Backend API & Server Logic
│   ├── config.py                 # Configuration and environment loader
│   ├── logging_config.py         # Structured logging configuration
│   └── main.py                   # FastAPI application and route endpoints
├── database/                     # Data Persistence Layer
│   ├── connection.py             # SQLAlchemy engine and session factories
│   ├── crud.py                   # High-performance CRUD operations
│   └── models.py                 # 15 relational database entities
├── data/                         # Local Data Directory
│   ├── ai_student_copilot.db     # SQLite production database
│   ├── uploads/                  # Ingested student materials
│   └── vector_store/             # Persistent TF-IDF vector indices
├── docs/                         # Extended System Documentation
│   ├── api.md                    # REST API OpenAPI specifications
│   ├── architecture.md           # In-depth architectural design
│   └── user_guide.md             # End-user operational manual
├── models/                       # Domain Models & Providers
│   └── ai_provider.py            # Gemini, OpenAI & Offline provider abstraction
├── rag/                          # Retrieval-Augmented Generation
│   ├── document_loader.py        # PDF, DOCX, TXT, MD, CSV loaders
│   └── vector_store.py           # TF-IDF & Cosine Similarity vector store
├── services/                     # Business Logic Services
│   ├── analytics_service.py      # Mastery tracking and knowledge graph
│   ├── autonomous_workflow.py    # 15-step autonomous exam prep loop
│   ├── document_service.py       # File validation and chunk indexing
│   ├── memory_service.py         # Long-term memory and redactor
│   ├── planner_service.py        # Timetable adaptation logic
│   └── quiz_service.py           # Exam evaluation and grading
├── tools/                        # Safe Sandboxed Tool Registry
│   ├── calculator.py             # Safe AST mathematical evaluator
│   ├── document_reader.py        # Page-by-page document reader
│   ├── python_sandbox.py         # AST-filtered secure code executor
│   ├── quiz_generator.py         # Automated question synthesizer
│   ├── registry.py               # Tool registry and audit logging
│   ├── report_generator.py       # HTML and Markdown report exporter
│   ├── semantic_search.py        # Local vector index query tool
│   ├── tabular_reader.py         # CSV/Excel statistical analyzer
│   ├── task_state_manager.py     # Goal and task state updater
│   └── web_research.py           # Permitted domain academic research
├── ui/                           # Streamlit User Interface Components
│   ├── agents_view.py            # Multi-agent trace and explainability
│   ├── analytics_view.py         # Progress charts and weakness matrix
│   ├── dashboard.py              # Main student dashboard
│   ├── diagnostics_view.py       # System health and debugging
│   ├── goals_view.py             # Academic goals & autonomous launcher
│   ├── knowledge_view.py         # Document retrieval explorer
│   ├── materials.py              # File uploader and chunk previewer
│   ├── memory_view.py            # Student memory & profile editor
│   ├── planner_view.py           # Day-by-day timetable
│   ├── profile.py                # Student biographical settings
│   ├── quizzes_view.py           # Practice exams and mock tests
│   ├── reports_view.py           # Exam readiness report viewer
│   ├── settings_view.py          # Model and application configuration
│   ├── subjects.py               # Subject and curriculum manager
│   └── tutor.py                  # Conversational AI tutor
├── app.py                        # Streamlit main entrypoint
├── requirements.txt              # Production Python package manifest
├── verify_phase1.py              # Phase 1 verification script
├── verify_phase2.py              # Phase 2 verification script
└── verify_phase3.py              # Phase 3 verification script
```

---

## 🔒 Safety, Security & Sandboxing

1. **AST-Filtered Code Sandbox:** The `python_sandbox` tool parses submitted Python code into an Abstract Syntax Tree (AST) before execution. Any attempt to access `os`, `sys`, `subprocess`, `socket`, `builtins`, or `shutil` raises an immediate `SecurityError`. Execution is confined to a 3-second timeout thread.
2. **Safe Mathematical Evaluator:** The `calculator` tool parses expressions strictly through `ast.Expression` with an allowlist of unary and binary mathematical operations and math constants (`pi`, `e`, `sqrt`, `sin`, `cos`). Arbitrary method invocation or code injection is impossible.
3. **Secret Redaction:** The `MemoryManager` and `MemoryAgent` sanitize all conversation turns and memories through strict regex filters to scrub API keys (`AIza...`, `sk-...`), bearer tokens, passwords, and private identifiers prior to persistence.
4. **Audit Trail:** Every tool execution records timestamp, executing agent, input parameters, output summary, execution duration in milliseconds, and status directly in the `tool_calls` database table.

---

## 📄 License
This project is open-source under the MIT License.
