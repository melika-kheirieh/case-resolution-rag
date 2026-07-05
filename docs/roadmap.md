# Roadmap

## Current Demo Slice

Goal: make refund-delay cases run end-to-end through case loading, timeline generation, policy retrieval, evidence checks, SLA checks, and a structured `ResolutionPacket`.

Status: current demo slice complete.

Implemented:

- Synthetic happy-path and failure-path `refund_delay` cases
- Timeline generation
- Active policy retrieval
- Deterministic policy chunk embeddings
- Semantic policy retrieval through a vector-store interface
- Policy filtering by case type, policy version, and effective date
- PostgreSQL + pgvector adapter for policy chunks
- Docker Compose Postgres/pgvector run path
- Retrieval run metadata
- Expired policy rejection
- Policy conflict detection
- Missing evidence detection
- Refund failure detection
- SLA breach check
- Explicit risk gate with pass/fail, score, level, and reasons
- Structured resolution packet
- Case readiness status
- Automation decision and blockers
- Structured fake provider with bad-output simulation
- Customer-facing response gate
- Pytest-based domain and API test coverage
- Basic investigation logging
- Request and correlation ID propagation
- Structured JSON logs
- Durable investigation runs and ordered audit events
- Alembic migration for audit tables
- Failure gallery endpoint
- CI workflow for lint, compile, tests, and evaluation threshold checks
- Thin FastAPI demo routes
- Demo walkthrough
- Demo golden-case evaluation report
- Architecture note, data card, evaluation note, and demo walkthrough

Next:

- Add durable PostgreSQL models for support cases, refunds, and timeline events
- Add repository-backed case loading while preserving synthetic demo fixtures
- Add pagination beyond the current limit-based investigation run listing

## Persistence And Audit

Goal: move beyond the in-memory demo by adding durable storage, explicit audit records, and stronger workflow invariants.

Implemented:

- Durable investigation runs
- Durable audit events
- Alembic migration setup for audit tables
- Request ID and correlation ID propagation into persisted runs

Planned:

- PostgreSQL-backed repositories for operational case data
- Clearer domain invariants for evidence, policy, citation, and customer-response gating

## Evaluation And Operability

Goal: improve confidence in the system through broader evaluation cases, clearer run instructions, structured logs, and easier local inspection.

Planned:

- Expanded golden-case evaluation set
- Evaluation thresholds for action correctness, citation coverage, and abstention behavior
- Failure gallery documentation
- API examples for happy path and failure paths
- Docker Compose local run path
- Lightweight operational notes for logs, traces, and troubleshooting
