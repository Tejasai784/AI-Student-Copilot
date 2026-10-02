# ASIP V2.0 REST & Streaming API Documentation

## 1. Overview
The platform exposes a versioned REST API mounted under `/api/v1` with complete OpenAPI documentation available at `/docs` (Swagger UI) and `/redoc`.

All endpoints return a uniform envelope:
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional status message",
  "error": null
}
```

---

## 2. API Endpoints Reference

### 2.1 Authentication (`/api/v1/auth`)
- `POST /register`: Register user account.
- `POST /login`: Authenticate credentials, set HttpOnly cookies, and issue JWT tokens.
- `POST /refresh`: Refresh access token via refresh token.
- `POST /logout`: Revoke active refresh token and clear cookies.
- `GET /me`: Get authenticated user profile.

### 2.2 Student Profile & Settings (`/api/v1/students`)
- `GET /profile`: Get student academic identity (name, course, semester).
- `PUT /profile`: Update student academic profile.
- `GET /settings`: Get student learning preferences and style.
- `PUT /settings`: Update learning style, difficulty, session duration.
- `GET /dashboard`: Aggregated dashboard summary (upcoming exams, study progress, weak topics).

### 2.3 Subjects & Syllabus (`/api/v1/subjects`)
- `GET /`: List registered subjects with completion percentages.
- `POST /`: Register a new course subject.
- `GET /{id}`: Subject detail with unit-grouped syllabus topics.
- `POST /{id}/topics`: Add a syllabus topic to a unit.
- `PATCH /{id}/topics/{topic_id}/toggle`: Toggle completion status of a topic.

### 2.4 Documents & Vector Ingestion (`/api/v1/documents`)
- `GET /`: List uploaded documents with ingestion status.
- `POST /upload`: Multipart upload with MIME validation and background indexing.
- `GET /{id}`: Document detail and page count.
- `DELETE /{id}`: Atomic removal of file, chunks, and vector embeddings.
- `GET /{id}/chunks`: Inspect vector chunks for a document.
- `GET /search`: User-scoped semantic vector retrieval with citation excerpts.

### 2.5 Resilient Chat & Streaming (`/api/v1/chat`)
- `GET /stream`: Server-Sent Events (SSE) chat streaming endpoint.
- `GET /conversations`: List active chat conversations.
- `POST /conversations`: Create a new conversation session.
- `PATCH /conversations/{id}`: Rename a conversation title.
- `DELETE /conversations/{id}`: Delete conversation and associated messages.
- `GET /conversations/{id}/messages`: Retrieve message history and grounding citations.

### 2.6 Quizzes & Mock Exams (`/api/v1/quizzes`)
- `POST /generate`: Generate practice quiz or timed mock exam.
- `GET /{id}`: Fetch attempt details, questions, and options.
- `POST /{id}/answer`: Save an answer during an in-progress attempt.
- `POST /{id}/submit`: Submit attempt, calculate scores, and generate explanations.
- `GET /history/list`: Retrieve past quiz attempt scorecard history.

### 2.7 Study Planner (`/api/v1/study-plan`)
- `GET /`: Retrieve the active study plan and timeline.
- `POST /generate`: Generate an adaptive schedule based on weak topics and syllabus.
- `PATCH /tasks/{id}/toggle`: Check off or reopen a scheduled study task.

### 2.8 Goals & Autonomous Decomposition (`/api/v1/goals`)
- `GET /`: List academic goals and progress.
- `POST /`: Decompose natural language prompt into goals and milestones.
- `GET /{id}`: Goal details with ordered subtasks.
- `PATCH /tasks/{id}/toggle`: Toggle milestone completion.

### 2.9 Analytics & Weak Topics (`/api/v1/analytics`)
- `GET /performance`: Aggregate score velocity, accuracy, and subject breakdown.
- `GET /weak-topics`: Ranked list of error-prone syllabus topics.
- `GET /knowledge-map`: Topic mastery topology graph.

### 2.10 Readiness Reports (`/api/v1/reports`)
- `GET /exam-readiness`: Comprehensive academic readiness diagnostic report.
- `GET /download`: Export readiness report as `.md` or `.html`.

### 2.11 Long-Term Memory (`/api/v1/memory`)
- `GET /`: Retrieve personalized memory facts and preferences.
- `POST /`: Store a new personalized learning tendency.
- `DELETE /{id}`: Delete a memory fact.

### 2.12 Multi-Agent Orchestration (`/api/v1/agents`)
- `POST /orchestrate`: Dispatch query through planner, specialist agents, and evaluator.
- `POST /autonomous/prepare`: Autonomous workflow coordinator for goal preparation.
- `GET /runs`: List past agent execution runs.
- `GET /runs/{id}`: Full execution trace and external tool calls.
- `GET /tools`: List registered tools and JSON schemas.
- `POST /tools/execute`: Execute a registered tool directly with safety checks.

### 2.13 System Diagnostics & Health (`/api/v1/diagnostics`)
- `GET /health`: Liveness and readiness probe.
- `GET /system`: Table entity counts, vector chunk count, and disk storage metrics.
