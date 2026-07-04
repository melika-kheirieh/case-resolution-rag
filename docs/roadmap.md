# Roadmap

## Current Demo Slice

Goal: make refund-delay cases run end-to-end through case loading, timeline generation, policy retrieval, evidence checks, SLA checks, and a structured `ResolutionPacket`.

Status: current demo slice complete.

Implemented:

- Synthetic happy-path and failure-path `refund_delay` cases
- Timeline generation
- Active policy retrieval
- Retrieval run metadata
- Expired policy rejection
- Policy conflict detection
- Missing evidence detection
- SLA breach check
- Structured resolution packet
- Case readiness status
- Automation decision and blockers
- Structured fake provider with bad-output simulation
- Customer-facing response gate
- Pytest-based domain and API test coverage
- Basic investigation logging
- Basic audit trace with retrieval and decision events
- Thin FastAPI demo routes
- Demo walkthrough
- Demo golden-case evaluation report

Next:

- Add more failure gallery cases
- Add request and correlation ID logging
- Replace in-memory store with PostgreSQL models
- Add Alembic migrations
- Add more evaluation scenarios and threshold checks
- Add structured JSON logs

## Persistence And Audit

Goal: move beyond the in-memory demo by adding durable storage, explicit audit records, and stronger workflow invariants.

Planned:

- PostgreSQL-backed repositories
- Alembic migration setup
- Durable investigation runs
- Durable audit events
- Clearer domain invariants for evidence, policy, citation, and customer-response gating
- Request ID and correlation ID propagation
- Structured JSON logging

## Evaluation And Operability

Goal: improve confidence in the system through broader evaluation cases, clearer run instructions, structured logs, and easier local inspection.

Planned:

- Expanded golden-case evaluation set
- Evaluation thresholds for action correctness, citation coverage, and abstention behavior
- Failure gallery documentation
- API examples for happy path and failure paths
- Docker Compose local run path
- Lightweight operational notes for logs, traces, and troubleshooting
