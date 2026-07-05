from datetime import UTC, datetime
import sys
from types import SimpleNamespace

from app.services.pgvector_store import PostgresPolicyVectorStore


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, calls):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))
        if "1 - (embedding <=>" in sql:
            return FakeResult(
                [
                    (
                        "chunk_current",
                        "policy_current",
                        "Refund Policy",
                        "2026.07",
                        datetime(2026, 6, 1, tzinfo=UTC),
                        None,
                        "Current refund SLA is 3 days.",
                        {"case_type": "refund_delay", "refund_sla_days": 3},
                        0.99,
                    )
                ]
            )
        return FakeResult([("policy_wrong_version",), ("policy_expired",)])


def test_pgvector_search_filters_active_version_and_reports_rejected_versions(monkeypatch):
    calls = []
    fake_psycopg = SimpleNamespace(connect=lambda database_url: FakeConnection(calls))
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    effective_at = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)

    result = PostgresPolicyVectorStore(
        database_url="postgresql://case_resolution@example/case_resolution"
    ).search(
        query="refund delay",
        case_type="refund_delay",
        effective_at=effective_at,
        policy_version="2026.07",
        top_k=3,
    )

    active_sql, active_params = calls[0]
    rejected_sql, rejected_params = calls[1]
    assert "AND version = %s" in active_sql
    assert "effective_from <= %s" in active_sql
    assert "OR %s < effective_to" in active_sql
    assert active_params[1:5] == ("refund_delay", "2026.07", effective_at, effective_at)
    assert active_params[-1] == 3
    assert "OR version <> %s" in rejected_sql
    assert rejected_params == ("refund_delay", effective_at, effective_at, "2026.07")
    assert result.matches[0].policy.id == "policy_current"
    assert result.rejected_policy_ids == ["policy_wrong_version", "policy_expired"]
