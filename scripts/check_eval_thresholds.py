from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass(frozen=True)
class MetricThreshold:
    metric_name: str
    minimum: float


THRESHOLDS = [
    MetricThreshold("action_accuracy", 1.0),
    MetricThreshold("decision_accuracy", 1.0),
    MetricThreshold("retrieval_hit_rate", 1.0),
    MetricThreshold("citation_coverage", 1.0),
    MetricThreshold("manual_review_accuracy", 1.0),
    MetricThreshold("unsafe_response_block_rate", 1.0),
    MetricThreshold("abstention_accuracy", 1.0),
]


def main() -> int:
    from app.services.demo_seed import build_demo_store
    from app.services.evaluation import run_demo_evaluation
    from app.services.investigation import InvestigationService

    store = build_demo_store()
    report = run_demo_evaluation(InvestigationService(store=store))
    failures = []

    if report.passed_cases != report.total_cases:
        failures.append(
            {
                "metric": "passed_cases",
                "minimum": report.total_cases,
                "actual": report.passed_cases,
            }
        )

    for threshold in THRESHOLDS:
        actual = getattr(report, threshold.metric_name)
        if actual < threshold.minimum:
            failures.append(
                {
                    "metric": threshold.metric_name,
                    "minimum": threshold.minimum,
                    "actual": actual,
                }
            )

    payload = {
        "total_cases": report.total_cases,
        "passed_cases": report.passed_cases,
        "thresholds": [threshold.__dict__ for threshold in THRESHOLDS],
        "failures": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
