# Case Resolution RAG

Evidence-based case resolution backend for e-commerce refund delays.

This is a small demo slice of an AI-first operations case resolution backend. It is not a
production system.

This project is not a chatbot, payment processor, PSP integration, or bank simulator. It is a backend workflow that loads an operational support case, builds a timeline, retrieves active policy evidence, checks refund SLA, proposes a structured action, drafts a customer-safe response, and records an investigation trace.

## Current Slice

Implemented demo slice:

- Multiple synthetic `refund_delay` demo cases
- Synthetic order, payment, return, and refund events
- Active refund policy retrieval with deterministic embeddings and semantic ranking
- `DocumentChunk` embeddings for policy chunks
- PostgreSQL + pgvector-backed policy chunk store for Docker Compose runs
- In-memory vector store for fast tests and API-key-free local development
- Retrieval run metadata with matched and rejected policy ids
- Policy conflict detection
- Refund failure detection
- Explicit `risk_gate` with score, level, pass/fail, and reasons
- SLA breach detection
- Structured `ResolutionPacket`
- Case readiness status
- `automation_decision` and `automation_blockers`
- Deterministic fake LLM provider with safe and bad-output modes
- Customer response gate that requires citation, safe decision, and structured provider output
- In-memory audit trace with retrieval and decision events
- Basic investigation logging for case id, retrieved chunk ids, decision, and blockers
- Demo evaluation report over golden cases
- Evaluation metrics for action, decision, retrieval hit, citation, manual review, unsafe response blocking, and abstention behavior
- Failure gallery endpoint for inspecting unsafe and manual-review scenarios
- Thin FastAPI routes for health, demo case, investigation, failure gallery, and evaluation
- Pytest-based service/domain and API test coverage

Demo cases:

- `case_refund_delay_002`: completed refund, active policy, auto-resolution candidate
- `case_refund_delay_001`: pending refund beyond SLA, manual review required
- `case_refund_delay_missing_evidence`: missing refund request, manual review required
- `case_refund_delay_expired_policy`: expired policy is not used, manual review required
- `case_refund_delay_policy_conflict`: conflicting active policies, manual review required
- `case_refund_delay_refund_failed`: failed refund, manual review required
- `case_refund_delay_within_sla`: pending refund still inside SLA, wait/manual-review path
- `case_refund_delay_policy_version_mismatch`: active policy rejected because requested version does not match

Additional evaluation scenario:

- `bad_ai_response`: completed refund with a bad provider draft, blocked before customer response

## Why This Is Not Just A Chatbot

The LLM-shaped provider does not own the decision. It only drafts a structured customer response. The backend owns policy retrieval, evidence checks, SLA evaluation, automation blockers, citation gating, and the final `ResolutionPacket`.

That means a provider can produce a bad draft and the system can still block customer-facing output. This is the important contract: AI output is treated as an input to validate, not as the source of truth.

Day-four behavior focuses on failure paths: missing evidence, expired policy, conflicting policy, failed refund, SLA breach, and unsafe provider output are visible and test-covered.

## Enterprise RAG Boundary

This is not a full enterprise RAG platform yet. It does not include access control, document ingestion, reranking, or production-grade persistence for investigation runs.

It is still close to an enterprise RAG workflow because the core behavior is present:

- Policy chunks have deterministic embeddings.
- Docker Compose can run policy chunk retrieval through PostgreSQL + pgvector.
- Retrieval is scoped by case type, policy version, and active policy dates.
- Decisions require citations from retrieved policy chunks.
- Expired policy is rejected before decision-making.
- Conflicting active policies are escalated instead of silently choosing one.
- Missing evidence routes the case to human review.
- Failed refunds route to human review before retry or compensation handling.
- Unsafe or unstructured provider output blocks customer-facing response.
- Risk gating is explicit in the packet, not hidden inside prose.
- The packet carries trace data so the investigation path is inspectable.
- Requests carry `X-Request-ID` and `X-Correlation-ID` through response headers,
  structured logs, and investigation packets.
- CI runs lint, compile checks, tests, and the demo evaluation threshold gate.

## Non-Goals

- No real payments
- No real refunds
- No PSP, bank, Stripe, Shopify, or merchant integration
- No real customer PII
- No final financial decision made by AI
- No Kafka, LangChain, LangGraph, React, or microservices in this first slice

## Run

Install dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest -q
```

Run lint and compile checks:

```bash
python -m ruff check .
python -m compileall app tests
```

Run the evaluation quality gate used by CI:

```bash
python scripts/check_eval_thresholds.py
```

Run API:

```bash
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/demo
```

Or call the main investigation endpoint:

```bash
curl -X POST http://127.0.0.1:8000/cases/case_refund_delay_002/investigate
```

Or run the demo evaluation report:

```bash
curl http://127.0.0.1:8000/eval/demo
```

`/eval/demo` is a small demo evaluation report over the seeded golden cases. It is not a
production evaluation framework.

Or inspect the failure gallery:

```bash
curl http://127.0.0.1:8000/demo/failure-gallery
```

Useful project notes:

- `docs/architecture.md`
- `docs/evaluation.md`
- `docs/data-card.md`
- `docs/demo-script.md`

## PostgreSQL + pgvector Demo

The default direct Python run uses the in-memory vector store so tests and local iteration stay fast.

Docker Compose runs the API with PostgreSQL + pgvector:

```bash
docker compose up --build
```

On startup, the API creates the `vector` extension, creates the `policy_chunks` table, seeds the demo policy chunks with deterministic embeddings, and uses pgvector cosine similarity for policy retrieval.

The important boundary is the same in both modes: citations are rendered from backend metadata, not invented by the provider.

## Demo Journey

The investigation flow is:

1. Load case
2. Build timeline
3. Retrieve active refund policy by embedding similarity with case-type, policy-version, and effective-date filters
4. Check evidence completeness
5. Check case readiness and policy conflicts
6. Check refund SLA
7. Validate recommended action
8. Generate structured customer response draft
9. Build automation blockers
10. Run risk gate over blockers, citations, and action
11. Build automation decision
12. Gate customer-facing response using citation and provider-safety checks
13. Return a structured resolution packet
14. Store audit and retrieval trace for the investigation run

The output packet includes:

* `summary`
* `request_id`
* `correlation_id`
* `timeline`
* `evidence`
* `citations`
* `retrieval_run`
* `readiness`
* `risk_gate`
* `automation_decision`
* `automation_blockers`
* `requires_human_review`
* `customer_safe_response`
* `customer_response_allowed`
* `limitations`
* `trace`

## Demo Walkthrough

Suggested flow:

1. Run `case_refund_delay_002` and show that a completed refund with active policy citation becomes `auto_resolve_candidate`.
2. Point at `citations`, `retrieval_run.matched_chunk_ids`, and `customer_response_allowed`.
3. Run `case_refund_delay_001` and show that an SLA breach becomes `manual_review_required`.
4. Run `case_refund_delay_refund_failed` and show that a failed refund is not auto-resolved even with policy evidence.
5. Run `case_refund_delay_policy_conflict` and show that conflicting active policies are not auto-picked.
6. Run `/demo/failure-gallery` and show the failure modes in one response.
7. Run `/eval/demo` and show the 9-case golden report.
8. Explain the design sentence: "The provider drafts text, but the backend owns evidence, policy, citations, blockers, risk gate, and the final automation decision."

More detail is available in `docs/demo-script.md`.

## Operability Checks

The API adds a request ID and correlation ID to every response. If the caller
does not send them, the middleware generates a request ID and reuses it as the
correlation ID. Investigation packets include both fields so a demo response can
be connected to structured JSON logs.

The CI workflow runs:

* `python -m ruff check .`
* `python -m compileall app tests scripts`
* `python -m pytest -q`
* `python scripts/check_eval_thresholds.py`

The evaluation threshold script fails if any golden scenario fails or if action,
decision, retrieval, citation, manual-review, unsafe-output, or abstention
metrics drop below `1.0`.

## Data Realism

The data is synthetic and reproducible. The first slice intentionally avoids banking and PSP semantics. It uses e-commerce shaped events such as order placed, payment captured, return requested, refund requested, and refund pending.

Anything that looks like a customer identifier is masked and synthetic.

More detail is available in `docs/data-card.md`.
