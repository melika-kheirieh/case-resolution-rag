from datetime import UTC, datetime

from sqlalchemy import create_engine

from app.services.audit_repository import InvestigationAuditRepository, InvestigationRunRow
from app.services.demo_seed import build_demo_store
from app.services.investigation import InvestigationService


def test_audit_repository_persists_investigation_run():
    engine = create_engine("sqlite:///:memory:")
    repository = InvestigationAuditRepository.from_engine(engine)
    repository.ensure_schema()
    service = InvestigationService(
        store=build_demo_store(),
        audit_repository=repository,
    )

    packet = service.run("case_refund_delay_policy_conflict")
    persisted_run = repository.get(packet.investigation_run_id)

    assert persisted_run is not None
    assert persisted_run.id == packet.investigation_run_id
    assert persisted_run.case_id == packet.case_id
    assert persisted_run.recommended_action == packet.recommended_action
    assert persisted_run.automation_decision == packet.automation_decision
    assert persisted_run.risk_level == packet.risk_gate.risk_level
    assert persisted_run.risk_score == packet.risk_gate.score
    assert persisted_run.requires_human_review is True
    assert persisted_run.created_at.tzinfo is UTC
    assert [event.name for event in persisted_run.audit_events] == packet.trace
    assert all(event.created_at.tzinfo is UTC for event in persisted_run.audit_events)


def test_audit_repository_returns_none_for_missing_run():
    engine = create_engine("sqlite:///:memory:")
    repository = InvestigationAuditRepository.from_engine(engine)
    repository.ensure_schema()

    assert repository.get("inv_missing") is None


def test_audit_repository_list_recent_returns_latest_limited_run():
    engine = create_engine("sqlite:///:memory:")
    repository = InvestigationAuditRepository.from_engine(engine)
    repository.ensure_schema()
    _persist_run(
        repository,
        run_id="inv_older",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    _persist_run(
        repository,
        run_id="inv_newer",
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
    )

    recent_runs = repository.list_recent(limit=1)

    assert [run.id for run in recent_runs] == ["inv_newer"]


def _persist_run(
    repository: InvestigationAuditRepository,
    *,
    run_id: str,
    created_at: datetime,
) -> None:
    with repository.session_factory.begin() as session:
        session.add(
            InvestigationRunRow(
                id=run_id,
                case_id=f"case_{run_id}",
                provider_name="fake_provider",
                created_at=created_at,
                request_id=f"req_{run_id}",
                correlation_id=f"corr_{run_id}",
                recommended_action="resolve",
                automation_decision="auto_resolve_candidate",
                risk_level="low",
                risk_score=0,
                customer_response_allowed=True,
                requires_human_review=False,
                audit_reference="case_loaded > packet_returned",
            )
        )
