# Synthetic Data Card

## Purpose

The data exists to demonstrate a controlled backend workflow for refund-delay case resolution.

## Dataset Type

All cases, customers, orders, payments, refunds, events, and policies are synthetic.

## Included Scenarios

- Completed refund
- Pending refund beyond SLA
- Pending refund within SLA
- Missing refund record
- Expired policy
- Policy version mismatch
- Conflicting active policies
- Failed refund
- Bad provider output evaluation scenario

## Privacy

There is no real customer PII. Masked customer identifiers such as `cust_***_4821` are synthetic.

## Scope Limits

The dataset does not model real PSP behavior, real bank settlement, merchant-specific rules, fraud, chargebacks, or regional compliance. Amounts and timestamps are chosen to exercise workflow behavior, not to represent a production distribution.

## Reproducibility

The seed data is deterministic and lives in `app/services/demo_seed.py`. Policy chunk embeddings use the deterministic local embedding model so tests can run without an API key.
