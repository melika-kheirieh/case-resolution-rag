# Case Resolution RAG

Evidence-based case resolution backend for e-commerce refund delays.

This is a small demo slice of an AI-first operations case resolution backend. It is not a
production system.

This project is not a chatbot, payment processor, PSP integration, or bank simulator. It is a backend workflow that loads an operational support case, builds a timeline, retrieves active policy evidence, checks refund SLA, proposes a structured action, drafts a customer-safe response, and records an investigation trace.

## Current Slice

Implemented demo slice:

- Multiple synthetic `refund_delay` demo cases
- Synthetic order, payment, return, and refund events
- Active refund policy retrieval with chunk citation
- Retrieval run metadata with matched and rejected policy ids
- Policy conflict detection
- SLA breach detection
- Structured `ResolutionPacket`
- Case readiness status
- `automation_decision` and `automation_blockers`
- Deterministic fake LLM provider with safe and bad-output modes
- Customer response gate that requires citation, safe decision, and structured provider output
- In-memory audit trace with retrieval and decision events
- Basic investigation logging for case id, retrieved chunk ids, decision, and blockers
- Demo evaluation report over golden cases
- Thin FastAPI routes for health, demo case, investigation, and evaluation
- Pytest-based service/domain and API test coverage

Demo cases:

- `case_refund_delay_002`: completed refund, active policy, auto-resolution candidate
- `case_refund_delay_001`: pending refund beyond SLA, manual review required
- `case_refund_delay_missing_evidence`: missing refund request, manual review required
- `case_refund_delay_expired_policy`: expired policy is not used, manual review required
- `case_refund_delay_policy_conflict`: conflicting active policies, manual review required

## Why This Is Not Just A Chatbot

The LLM-shaped provider does not own the decision. It only drafts a structured customer response. The backend owns policy retrieval, evidence checks, SLA evaluation, automation blockers, citation gating, and the final `ResolutionPacket`.

That means a provider can produce a bad draft and the system can still block customer-facing output. This is the important contract: AI output is treated as an input to validate, not as the source of truth.

## Enterprise RAG Boundary

This is not a full enterprise RAG platform yet. It does not include vector search, access control, document ingestion, reranking, or production persistence.

It is still close to an enterprise RAG workflow because the core behavior is present:

- Retrieval is scoped by case type and active policy dates.
- Decisions require citations from retrieved policy chunks.
- Expired policy is rejected before decision-making.
- Conflicting active policies are escalated instead of silently choosing one.
- Missing evidence routes the case to human review.
- Unsafe or unstructured provider output blocks customer-facing response.
- The packet carries trace data so the investigation path is inspectable.

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
python -m ruff check app tests
python -m compileall app tests
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

## Demo Journey

The investigation flow is:

1. Load case
2. Build timeline
3. Retrieve active refund policy
4. Check evidence completeness
5. Check case readiness and policy conflicts
6. Check refund SLA
7. Validate recommended action
8. Build automation decision and blockers
9. Generate structured customer response draft
10. Gate customer-facing response using citation and provider-safety checks
11. Return a structured resolution packet
12. Store audit and retrieval trace for the investigation run

The output packet includes:

* `summary`
* `timeline`
* `evidence`
* `citations`
* `retrieval_run`
* `readiness`
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
4. Run `case_refund_delay_policy_conflict` and show that conflicting active policies are not auto-picked.
5. Run `/eval/demo` and show the golden-case report.
6. Explain the design sentence: "The provider drafts text, but the backend owns evidence, policy, citations, blockers, and the final automation decision."

More detail is available in `docs/demo-script.md`.

## Data Realism

The data is synthetic and reproducible. The first slice intentionally avoids banking and PSP semantics. It uses e-commerce shaped events such as order placed, payment captured, return requested, refund requested, and refund pending.

Anything that looks like a customer identifier is masked and synthetic.
