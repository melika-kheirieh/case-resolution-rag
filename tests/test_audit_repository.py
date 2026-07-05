from datetime import UTC

from sqlalchemy import create_engine

from app.services.audit_repository import InvestigationAuditRepository
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
