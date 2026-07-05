# Evaluation Note

The demo evaluation uses 9 golden scenarios. It is intentionally small, but it makes the expected behavior explicit and regression-testable.

## Covered Scenarios

- Auto-resolution candidate
- SLA breach
- Missing refund evidence
- Expired policy
- Conflicting active policies
- Failed refund
- Pending refund still inside SLA
- Policy version mismatch
- Bad provider output

## Metrics

- `action_accuracy`: expected recommended action matches the packet.
- `decision_accuracy`: expected automation decision matches the packet.
- `retrieval_hit_rate`: expected retrieval-hit behavior matches the packet.
- `citation_coverage`: expected citation presence matches the packet.
- `manual_review_accuracy`: expected human-review routing matches the packet.
- `unsafe_response_block_rate`: expected unsafe provider blocking matches the packet.
- `abstention_accuracy`: expected no-customer-response behavior matches the packet.

## CI Threshold Gate

The repository includes `scripts/check_eval_thresholds.py` so evaluation is not
only a demo endpoint. CI fails if any golden scenario fails or if any metric
drops below `1.0`.

Current enforced metrics:

- `action_accuracy`
- `decision_accuracy`
- `retrieval_hit_rate`
- `citation_coverage`
- `manual_review_accuracy`
- `unsafe_response_block_rate`
- `abstention_accuracy`

## Why These Metrics

Action correctness alone is not enough for an AI backend. A system can recommend the right action and still be unsafe if it allows an unsupported customer response. That is why the evaluation separates recommendation, decision, citation, manual review, and unsafe-output blocking.

## Current Limitations

The golden set is synthetic and small. It is useful for regression and demo walkthroughs, not for production confidence. A production version would add more realistic case distributions, policy documents, retrieval labels, adversarial provider outputs, and threshold checks in CI.
