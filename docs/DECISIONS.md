# Architecture Decision Records (ADRs)

## ADR-001: Modular FastAPI Routers & Versioned API
- **Status**: Accepted
- **Context**: V1 had monolithic routes mixed inside `main.py` without schema validation or route grouping.
- **Decision**: Split endpoints into 14 distinct routers under `backend/routers/` prefixed with `/api/v1`.
- **Consequences**: Enhanced testability, clear boundary separation, and automatic OpenAPI schema generation.

---

## ADR-002: Dual AI Provider Manager with Circuit Breaker
- **Status**: Accepted
- **Context**: Relying exclusively on a single AI provider introduces single point of failure (rate limits, outages).
- **Decision**: Implement an AI Provider Manager using Google Gemini 2.5 Flash as primary with circuit breaker tracking (3 failures threshold, 60s cooldown) and automatic model-level fallback chain to OpenAI GPT-4o-mini.
- **Consequences**: Zero downtime for student tutoring during provider disruptions.

---

## ADR-003: Ingestion Pipeline with Magic Bytes & UUID Storage Isolation
- **Status**: Accepted
- **Context**: Uploaded files risked extension spoofing, path traversal, and file collisions.
- **Decision**: Validate MIME headers via magic byte inspection, store files with randomized UUIDs on disk, and track ingestion stages (`UPLOADING` $\rightarrow$ `PROCESSING` $\rightarrow$ `INDEXING` $\rightarrow$ `READY`/`FAILED`).
- **Consequences**: Protection against malicious file uploads and robust asynchronous indexing.

---

## ADR-004: Hardened AST Sandbox for Tool Execution
- **Status**: Accepted
- **Context**: Agents required mathematical and algorithmic tool execution without risking host command execution.
- **Decision**: Built a Python AST sandbox parser that forbids dangerous AST nodes, restricts builtins, enforces depth limits, and runs within a time-bounded threadpool.
- **Consequences**: Complete protection against RCE and resource exhaustion attacks.

---

## ADR-005: SSE Streaming Protocol with Keepalive Ping & Provider Switch Recovery
- **Status**: Accepted
- **Context**: Long-running LLM generation was subject to proxy timeouts, and mid-stream provider failures broke user sessions.
- **Decision**: Built `/api/v1/chat/stream` using Server-Sent Events with 15-second keepalive pings, custom `trace`, `chunk`, `citation`, and mid-stream `provider_switch` event recovery.
- **Consequences**: Reliable, seamless streaming UX with real-time agent visibility.

---

## ADR-006: React 18 + Vite + Tailwind with Calm Study Studio Design Tokens
- **Status**: Accepted
- **Context**: Streamlit UI lacked granular component reactivity and layout customization for study workflows.
- **Decision**: Built a responsive modern frontend using React 18, TypeScript, Vite, Tailwind CSS with the §7A Calm Study Studio color tokens (`ink #14213D`, `canvas #F4F6FA/#0E1424`, `focus #0F8B8D`, `spark #F2A93B`, `weak #D64561`, `good #3FA66B`) and self-hosted fonts.
- **Consequences**: Sub-second UI responsiveness, WCAG AA accessibility, zero external CDN reliance.

---

## ADR-007: SQLite with WAL Mode & Alembic Migration Tracking
- **Status**: Accepted
- **Context**: Database changes needed reliable version control without risking data corruption during concurrent reads.
- **Decision**: Adopted SQLite with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and Alembic migration scripts.
- **Consequences**: Zero data loss, painless schema evolution, and high concurrency for local and containerized deployments.
