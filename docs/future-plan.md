# Future Plan

This document keeps future scope separate from the current demo slice. The current project should stay small, runnable, and evidence-driven. Future work should deepen the same core instead of turning the project into a generic chatbot, payment simulator, or oversized platform.

## Product Direction

The long-term direction is an AI-first operations case resolution backend.

The system should help resolve routine operational cases when evidence is complete, policy is clear, and the risk is low. It should route ambiguous, conflicting, incomplete, or high-risk cases to human review.

The provider may draft text, classify signals, or summarize evidence, but the backend owns:

- Evidence loading
- Policy retrieval
- Citation rendering
- SLA checks
- Automation blockers
- Readiness status
- Customer response gating
- Audit trace
- Evaluation

## Near-Term Improvements

The next improvements should focus on behavior, not infrastructure for its own sake:

- Add more refund-delay failure scenarios.
- Persist investigation runs and audit events.
- Add PostgreSQL-backed case and refund repositories.
- Add Alembic migrations for durable state.
- Add API examples for tracing requests through logs and packets.

## Persistence

The current slice uses an in-memory store to keep the demo fast. A later durable iteration can add PostgreSQL with SQLAlchemy and Alembic.

Useful tables:

- `support_cases`
- `refund_requests`
- `timeline_events`
- `policy_documents`
- `document_chunks`
- `investigation_runs`
- `audit_events`
- `evaluation_runs`

The repository interfaces already make this migration easier because application services do not need to know whether data comes from memory or a database.

## Retrieval

The current retrieval is vector-store-backed and metadata-aware, with deterministic embeddings for fast local tests and pgvector for the Docker Compose path. A later iteration can add:

- Keyword search
- Hybrid retrieval
- Reranking
- Parent-child chunk retrieval
- Version-aware policy filtering
- Citation coverage checks

The important rule should stay the same: a customer-facing answer must not be allowed without supporting policy evidence.

## Safety And Evaluation

Evaluation should grow with every new capability.

Useful checks:

- Expected recommended action
- Expected automation decision
- Expected readiness status
- Citation presence
- Abstention behavior
- Unsafe response blocking
- Policy conflict handling

The current CI gate keeps the synthetic golden set strict. Future production-like
evaluation should add larger and messier datasets before relaxing or weighting
thresholds.

The evaluation report should separate action correctness from automation safety. A system can choose the right action but still be unsafe if it allows an unsupported customer response.

## Automation Scope

Automation should be conservative.

Good automation candidates:

- Low-risk cases
- Complete evidence
- Active policy citation
- No policy conflict
- Completed refund or clearly safe status
- Structured provider output

Manual review should trigger for:

- Missing evidence
- Expired or missing policy
- Conflicting active policies
- SLA breach
- Unsafe provider output
- Low confidence
- Ambiguous customer-facing promise

## Later Architecture

After the core behavior is stronger, the project can grow toward:

- Outbox pattern for reliable domain events
- Worker-based evaluation or ingestion jobs
- Audit projections
- Lightweight analytics
- Optional event streaming after the outbox exists
- Service extraction only after clear boundaries emerge

Kafka, Kubernetes, and service extraction should come after the product behavior is worth scaling.

## Non-Goals

This project should not claim:

- Real payment processing
- Real refund execution
- Real PSP or bank integration
- Real customer PII
- Fully autonomous financial decisions
- Full enterprise RAG
- Regulated-compliance guarantees

The project should stay honest: a safe, inspectable backend demo for evidence-based case resolution.
