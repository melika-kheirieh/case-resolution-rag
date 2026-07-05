# Demo Script

This script is for a short project walkthrough. The goal is to show that this is a controlled backend workflow, not a chatbot demo.

## Setup

Run the API:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/demo
```

## Three-Minute Flow

1. Start with `case_refund_delay_002`.
   - Show `automation_decision = auto_resolve_candidate`.
   - Point to `citations`, `retrieval_run.matched_chunk_ids`, and `customer_response_allowed = true`.
   - Say: the backend allows the response because the refund is completed, policy evidence was retrieved through the vector store, citation metadata exists, and the provider output passed safety checks.

2. Run `case_refund_delay_001`.
   - Show `sla_check.is_breached = true`.
   - Show `automation_decision = manual_review_required`.
   - Point to `automation_blockers`.
   - Say: SLA breach is not auto-resolved because customer-facing promises need operator review.

3. Run `case_refund_delay_missing_evidence`.
   - Show `readiness.status = missing_evidence`.
   - Show `missing_refund_request`.
   - Say: the system abstains instead of inventing a refund status.

4. Run `case_refund_delay_policy_conflict`.
   - Show `retrieval_run.status = policy_conflict`.
   - Show two citations and `conflict_policy_ids`.
   - Say: multiple active policies disagree, so the backend escalates instead of choosing one silently.

5. Run `/eval/demo`.
   - Show `action_accuracy`, `citation_coverage`, and `abstention_accuracy`.
   - Say: the evaluation is small, but it makes the expected behavior explicit and regression-testable.

## Closing Sentence

"Policy chunks are embedded and can be retrieved through pgvector, but the provider still only drafts text; the backend owns evidence, policy selection, citation checks, blockers, readiness, and the final automation decision."
