# Architecture Note

This project is a small, evidence-first backend workflow for refund-delay case resolution.

## Boundary

The provider drafts customer-facing text, but it does not own the decision. The backend owns case loading, evidence checks, policy retrieval, citation rendering, SLA checks, risk gating, response gating, and the final `ResolutionPacket`.

## Flow

1. Load the support case from the demo store.
2. Build the operational timeline.
3. Retrieve active policy chunks through the vector-store interface.
4. Filter retrieval by case type, policy version, and policy effective date.
5. Build policy citations from backend metadata.
6. Check missing evidence, policy conflict, SLA breach, refund failure, and provider output shape.
7. Run the risk gate.
8. Decide whether the case is an auto-resolution candidate or needs human review.
9. Return a structured packet with evidence, citations, blockers, risk, limitations, and audit trace.
10. Persist the investigation run and ordered audit events for later inspection.

## Storage

The default local path uses an in-memory store for source case/refund fixtures so
tests stay fast and deterministic. Policy retrieval can run through PostgreSQL
and pgvector in Docker Compose.

Investigation audit is durable. The app stores `investigation_runs` and ordered
`audit_events` through SQLAlchemy. Local direct runs use SQLite by default, while
Docker/PostgreSQL runs can use `DATABASE_URL` or a dedicated `AUDIT_DATABASE_URL`.

## Safety Invariants

- No customer-facing response without a policy citation.
- No auto-resolution when evidence is missing.
- No auto-resolution when active policies conflict.
- No auto-resolution when refund movement failed.
- No auto-resolution when the provider returns unsafe or unstructured text.
- The backend renders citations; the provider does not invent them.
- Audit events are written after the final packet is built, so the persisted run
  reflects the actual returned decision.

## Deliberate Non-Goals

This slice does not implement real payment processing, real refund execution, real customer PII, auth, multi-tenancy, or full enterprise ingestion. It is meant to demonstrate backend judgment around AI-assisted case resolution without overclaiming production readiness.
