# ASIP V2.0 Changelog

All notable changes to the Autonomous Student Intelligence Platform (ASIP) are documented in this file.

## [2.0.0] - 2026-10-02

### Added
- **Phase 0 (Audit & Planning)**: Comprehensive baseline audit (`docs/AUDIT.md`) and implementation roadmap (`implementation_plan.md`).
- **Phase 1 (Security, Auth & Routers)**:
  - Alembic SQLite database migration system.
  - JWT authentication with access/refresh tokens and HttpOnly cookies.
  - 14 modular routers under `/api/v1/*`.
  - Secret masking and safe exception handlers.
- **Phase 2 (AI Provider Manager)**:
  - Dual-engine circuit breaker manager with Google Gemini 2.5 Flash primary and OpenAI GPT-4o-mini fallback.
  - Exponential backoff and model-level fallback chain.
  - Non-leaking provider telemetry diagnostic endpoint.
- **Phase 3 (Upload Hardening & RAG Pipeline)**:
  - Binary magic-byte MIME validation for academic file formats.
  - UUID disk storage isolation protecting against path traversal.
  - Ingestion status pipeline (`UPLOADING` $\rightarrow$ `PROCESSING` $\rightarrow$ `INDEXING` $\rightarrow$ `READY`/`FAILED`).
  - User-scoped vector retrieval with validated chunk citations and excerpts.
- **Phase 4 (Safe Tool Registry & Agent Orchestration)**:
  - Hardened AST execution sandbox with node allowlisting and depth limits.
  - Pydantic-validated tool schemas for mathematical calculations, syllabus lookup, search, and quiz evaluation.
  - Explainable multi-agent orchestrator with state machine execution trace logging.
- **Phase 5 (Chat Streaming & SSE Protocol)**:
  - Resilient Server-Sent Events (SSE) streaming at `/api/v1/chat/stream`.
  - 15-second keepalive heartbeat ping.
  - Mid-stream `provider_switch` event recovery.
  - Conversation CRUD endpoints.
- **Phase 6 (React Frontend, Dashboard & AI Chat)**:
  - React 18, TypeScript, Vite, Tailwind CSS with §7A Calm Study Studio color palette.
  - Self-hosted typography (`@fontsource/bricolage-grotesque`, `figtree`, `jetbrains-mono`).
  - Asymmetric Today Dashboard with circular SVG progress meter.
  - Academic AI Tutor chat with streaming, source citations drawer, and agent trace timeline.
- **Phase 7 (Remaining Pages & Features)**:
  - Course Materials library with upload progress and vector chunk inspector.
  - Academic Knowledge Base with semantic search and topic mastery topology graph.
  - Syllabus & Topics unit tree and completion toggle.
  - Practice Quizzes generator with instant evaluation explanations.
  - Timed Mock Exams with live countdown timer and auto-submit upon expiry.
  - Adaptive Study Planner with daily/weekly calendar schedule.
  - Goals & Tasks with natural language autonomous decomposition.
  - Weak Topics detector with 1-click targeted remediation.
  - Progress Analytics with score velocity and subject mastery comparison bars.
  - Exam Readiness Reports with MD and HTML downloadable exports.
  - Personalization & Long-term Memory with privacy secret filter.
  - Multi-Agent Orchestration with live query execution and latency benchmarks.
  - Settings & Student Profile with WCAG AA theme toggle.
  - Developer Diagnostics with database WAL status and storage footprint.
- **Phase 8 (Hardening, Test Suite, Docs & Deployment)**:
  - Multi-stage production `Dockerfile` and `docker-compose.yml`.
  - Comprehensive automated test suite with 84 tests passing at 100%.
  - Complete documentation suite (`ARCHITECTURE.md`, `API.md`, `DEPLOYMENT.md`, `DECISIONS.md`, `CHANGELOG.md`).
  - Unified server serving both REST API and React Single Page App.

### Preserved
- Dual availability: Streamlit Community Cloud frontend preserved and functional via `app.py`.
- SQLite database backward compatibility and zero data loss guarantee.
