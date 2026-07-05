# Demo Script

Use this for a 3-5 minute technical walkthrough. The goal is to show a
controlled backend workflow, not a chatbot demo.

## Setup

Create the local environment and install dev dependencies:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Create the durable audit tables explicitly:

```bash
.venv/bin/python -m alembic upgrade head
```

Local direct runs use `case_resolution_audit.db` by default and also ensure the
demo audit tables exist at startup. Alembic is the explicit setup path.

## Run API

Start FastAPI:

```bash
.venv/bin/python -m uvicorn app.main:app --reload
```

Open the browser demo:

```text
http://127.0.0.1:8000/demo
```

## Resolve A Case

Run the completed-refund case:

```bash
curl -i -X POST \
  -H "X-Request-ID: req_demo_case_resolution" \
  -H "X-Correlation-ID: corr_case_resolution_demo" \
  http://127.0.0.1:8000/cases/case_refund_delay_002/investigate
```

Point out:

- `automation_decision = auto_resolve_candidate`
- `customer_response_allowed = true`
- `citations`
- `retrieval_run.matched_chunk_ids`
- `request_id` and `correlation_id` in response headers, packet fields, and JSON logs
- `investigation_run_id`

This is the real route for resolving a case in the current app. There is no
implemented `GET /resolve-case` endpoint.

## Inspect A Persisted Run

Copy `investigation_run_id` from the response and load the durable record:

```bash
curl http://127.0.0.1:8000/investigation-runs/{investigation_run_id}
```

Point out:

- persisted case id, decision, risk level, request id, and correlation id
- ordered `audit_events`
- `audit_reference`

List recent investigation runs:

```bash
curl "http://127.0.0.1:8000/investigation-runs?limit=20"
```

Point out that the response is `{"limit": 20, "runs": [...]}`.

## Show Failure Paths

Run one or two failure cases:

```bash
curl -X POST http://127.0.0.1:8000/cases/case_refund_delay_001/investigate
curl -X POST http://127.0.0.1:8000/cases/case_refund_delay_policy_conflict/investigate
```

For `case_refund_delay_001`, show:

- `sla_check.is_breached = true`
- `automation_decision = manual_review_required`
- `automation_blockers`
- `risk_gate.risk_level = high`

For `case_refund_delay_policy_conflict`, show:

- `retrieval_run.status = policy_conflict`
- two citations
- `conflict_policy_ids`

Optionally show the full failure gallery:

```bash
curl http://127.0.0.1:8000/demo/failure-gallery
```

## Run Eval Gate

Show the API report:

```bash
curl http://127.0.0.1:8000/eval/demo
```

Then run the same threshold gate used by local checks and CI:

```bash
.venv/bin/python scripts/check_eval_thresholds.py
```

Point out that all golden cases must pass and these metrics must stay at `1.0`:
`action_accuracy`, `decision_accuracy`, `retrieval_hit_rate`,
`citation_coverage`, `manual_review_accuracy`, `unsafe_response_block_rate`, and
`abstention_accuracy`.

## What This Proves

The backend, not the provider, owns evidence loading, policy retrieval, citation
rendering, SLA checks, blockers, risk gating, response gating, and the final
automation decision. Policy chunks can be retrieved through pgvector in the
Docker path, but provider output is still only a draft. The returned packet,
structured logs, persisted investigation run, ordered audit events, and eval
gate make the workflow inspectable and regression-testable.
