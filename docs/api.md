# ASIP REST API Specification

The **Autonomous Student Intelligence Platform (ASIP)** exposes a comprehensive, fully documented OpenAPI (REST) backend service powered by FastAPI.

Interactive documentation can be explored live at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 1. System & Telemetry Endpoints

### `GET /api/health`
Checks backend service availability, database connectivity, vector index chunk counts, and active AI model providers.
- **Response:**
  ```json
  {
    "status": "healthy",
    "app_name": "AI Student Copilot",
    "version": "2.0.0",
    "environment": "development",
    "database": "connected",
    "vector_store_chunks": 142,
    "ai_providers": ["Gemini (gemini-2.0-flash-lite)", "Offline Fallback"],
    "registered_tools_count": 9,
    "timestamp": "2026-09-29T16:00:00Z"
  }
  ```

### `GET /api/diagnostics`
Returns system diagnostics, database paths, registered tools, and masked credential statuses.

---

## 2. Student Profile & Curriculum Endpoints

### `GET /api/profile`
Retrieves the active student profile.

### `POST /api/profile`
Updates student academic metadata.
- **Request Body:**
  ```json
  {
    "name": "Jane Doe",
    "course": "B.Tech Computer Science",
    "branch": "Computer Science",
    "year": "3rd Year",
    "semester": "6th Semester"
  }
  ```

### `GET /api/subjects`
Lists registered subjects along with their syllabus units and topics.

### `POST /api/subjects`
Creates a new subject entry.
- **Request Body:**
  ```json
  {
    "name": "Python Programming",
    "code": "CS301",
    "semester": "6th Semester",
    "description": "Core course in Python syntax, OOP, and data structures."
  }
  ```

### `POST /api/subjects/{subject_id}/topics`
Appends a syllabus topic to a subject.

### `POST /api/topics/{topic_id}/toggle`
Toggles topic mastery / completion status.

---

## 3. Documents & Knowledge Base Endpoints

### `GET /api/documents`
Lists all uploaded course documents, status, page counts, chunk counts, and associated subject IDs.

### `POST /api/documents/upload`
Uploads and indexes academic documents. Supports `.pdf`, `.docx`, `.txt`, `.md`, and `.csv`.
- **Form Data:**
  - `file`: Binary file upload
  - `subject_id`: Integer
  - `unit_number`: Optional Integer
  - `topic_name`: Optional String
  - `document_type`: String (e.g., `"Syllabus"`, `"Question Paper"`, `"Lecture Notes"`)
- **Response:**
  ```json
  {
    "ok": true,
    "document_id": 4,
    "filename": "python_syllabus.txt",
    "status": "ready",
    "pages": 1,
    "chunks": 4
  }
  ```

### `DELETE /api/documents/{doc_id}`
Deletes the document record, associated files on disk, and unindexes chunks from the vector store.

---

## 4. AI Tutor & Conversations

### `POST /api/chat`
Interacts with the AI Tutor. Automatically performs semantic vector retrieval, injects relevant citations, records user/assistant dialogue in SQLite, and logs citations.
- **Request Body:**
  ```json
  {
    "query": "Can you explain Python decorators with a clean example?",
    "conversation_id": null,
    "subject_id": 1
  }
  ```
- **Response:**
  ```json
  {
    "ok": true,
    "conversation_id": 12,
    "reply": "A Python decorator is a callable that takes another function as an argument...",
    "model": "Gemini (gemini-2.0-flash-lite)",
    "grounded": true,
    "citations": [
      {"document_id": "4", "page": "1"}
    ]
  }
  ```

### `GET /api/conversations`
Lists past conversation sessions.

### `GET /api/conversations/{conv_id}/messages`
Fetches full chat history for a session.

---

## 5. Learning Goals & Study Planning

### `GET /api/goals`
Lists all learning goals, completion percentages, deadlines, and ordered subtasks.

### `POST /api/goals`
Decomposes an academic goal into a multi-day plan.
- **Request Body:**
  ```json
  {
    "title": "Python Exam Prep",
    "objective": "Prepare me for my Python exam in 7 days.",
    "days": 7,
    "subject_id": 1
  }
  ```

### `POST /api/tasks/{task_id}/toggle`
Toggles subtask completion status between `pending` and `completed`.

---

## 6. Multi-Agent Orchestration

### `POST /api/orchestrate`
Routes a complex student query through the AGI Orchestrator state machine.
- **Request Body:**
  ```json
  {
    "query": "Solve this equation: 3*x^2 - 12 = 0 and write a Python script to verify it",
    "subject_id": 1
  }
  ```
- **Response:**
  ```json
  {
    "ok": true,
    "query": "Solve this equation...",
    "intents": ["math", "coding"],
    "combined_summary": "...",
    "plan": ["MathAgent solving...", "CodingAgent verifying..."],
    "agent_run_id": 8,
    "evaluation": {
      "overall_score": 0.95,
      "feedback": "Correct derivation and working code."
    },
    "trace": [
      {
        "step_id": 1,
        "stage": "Plan",
        "agent": "PlannerAgent",
        "action": "Generated multi-step solution plan",
        "time": "2026-09-29T16:05:00Z"
      }
    ]
  }
  ```

### `GET /api/agents/runs`
Lists historical multi-agent execution runs with runtimes and tool invocation counts.

---

## 7. Safe Tools Execution

### `GET /api/tools`
Lists all 9 registered safe tools, their descriptions, and parameter JSON schemas.

### `POST /api/tools/execute`
Executes a registered tool directly with safety validation and audit logging.
- **Request Body:**
  ```json
  {
    "tool_name": "calculator",
    "arguments": {
      "expression": "sqrt(144) + 15 * 2"
    }
  }
  ```
- **Response:**
  ```json
  {
    "ok": true,
    "result": 42.0,
    "expression": "sqrt(144) + 15 * 2"
  }
  ```

---

## 8. Autonomous Exam Preparation (Primary Acceptance Benchmark)

### `POST /api/autonomous/prepare`
Executes the full 15-step autonomous exam preparation pipeline:
1. Ingests & inspects course materials
2. Identifies curriculum topics
3. Formulates day-by-day plan
4. Runs diagnostic exam
5. Discovers weaknesses
6. Dynamically adapts schedule
7. Injects remedial study tasks
8. Re-tests student
9. Updates long-term memory
10. Compiles explainable execution trace & readiness report

- **Request Body:**
  ```json
  {
    "goal_prompt": "Prepare me for my Python exam in 7 days. I have uploaded my syllabus and previous question papers.",
    "subject_id": 1
  }
  ```
- **Response:**
  ```json
  {
    "ok": true,
    "goal_id": 15,
    "goal_title": "Python Exam Prep (7 Days)",
    "days_planned": 7,
    "topics_discovered": ["Data Types", "Functions", "OOP & Classes", "File I/O"],
    "weaknesses_detected": ["OOP & Classes"],
    "schedule_adapted": true,
    "remedial_tasks_added": 1,
    "diagnostic_score": 60.0,
    "retest_score": 85.0,
    "predicted_readiness_score": 88.0,
    "execution_trace_steps": 15,
    "report_markdown": "# Exam Readiness Report...",
    "report_html": "<html>...</html>"
  }
  ```

---

## 9. Analytics, Memory & Reports

### `GET /api/analytics/performance`
Returns quiz attempt history, accuracy trends, and mastery distributions.

### `GET /api/analytics/weaknesses`
Returns detected academic weaknesses with priority rankings.

### `GET /api/analytics/knowledge-map`
Generates knowledge graph nodes and prerequisite edges for visual rendering.

### `GET /api/memory`
Lists stored student profile memories and personalizations.

### `POST /api/memory`
Stores a preference or learning attribute with automatic secret scrubbing.

### `DELETE /api/memory/{memory_id}`
Deletes a memory record.

### `GET /api/reports/readiness`
Generates a comprehensive readiness report for a subject in Markdown and HTML.
