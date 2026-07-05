from datetime import UTC, datetime

from app.domain.models import (
    AutomationDecision,
    CaseReadinessStatus,
    CaseStatus,
    DocumentChunk,
    PolicyDocument,
    RecommendedAction,
    SupportCase,
)
from app.services.embeddings import DeterministicEmbeddingModel
from app.services.evaluation import run_demo_evaluation
from app.services.investigation import InvestigationService
from app.services.policy_retrieval import PolicyRetrievalService
from app.services.provider import FakeProvider
from app.services.timeline import build_timeline


def test_demo_seed_contains_all_expected_cases(demo_store):
    case_ids = {support_case.id for support_case in demo_store.list_cases()}

    assert case_ids == {
        "case_refund_delay_001",
        "case_refund_delay_002",
        "case_refund_delay_missing_evidence",
        "case_refund_delay_expired_policy",
        "case_refund_delay_policy_conflict",
    }


def test_timeline_events_are_sorted_by_happened_at(demo_store):
    support_case = demo_store.get_case("case_refund_delay_001")
    timeline = build_timeline(demo_store.get_events_for_order(support_case.order_id))

    timestamps = [event.happened_at for event in timeline]

    assert timestamps == sorted(timestamps)


def test_active_refund_policy_retrieval_returns_expected_chunk_and_citation(demo_store):
    support_case = demo_store.get_case("case_refund_delay_001")

    result = PolicyRetrievalService().retrieve_active_refund_policy(
        support_case, demo_store.list_policies()
    )

    assert result.chunk is not None
    assert result.chunk.id == "chunk_refund_sla"
    assert result.citation is not None
    assert result.citation.chunk_id == "chunk_refund_sla"
    assert result.citation.document_id == "policy_refund_2026_summer"
    assert result.citation.title == "Refund and Return Policy v2026.06"
    assert result.citation.excerpt == result.chunk.text
    assert result.citations == [result.citation]
    assert result.retrieval_run.status == "policy_retrieved"
    assert result.retrieval_run.matched_chunk_ids == ["chunk_refund_sla"]


def test_seeded_policy_chunks_have_deterministic_embeddings(demo_store):
    chunks = [chunk for policy in demo_store.list_policies() for chunk in policy.chunks]

    assert chunks
    assert all(chunk.embedding for chunk in chunks)
    assert all(len(chunk.embedding) == DeterministicEmbeddingModel.dimensions for chunk in chunks)


def test_semantic_policy_retrieval_ranks_closest_chunk_first():
    embedding_model = DeterministicEmbeddingModel()
    support_case = SupportCase(
        id="case_semantic_rank",
        case_type="refund_delay",
        policy_version="2026.07",
        status=CaseStatus.OPEN,
        order_id="order_semantic",
        customer_id_masked="cust_***_semantic",
        customer_message="The refund is still pending after my return was accepted.",
        created_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )
    query = (
        f"{support_case.case_type} refund policy SLA evidence: "
        f"{support_case.customer_message}"
    )
    expected_chunk = DocumentChunk(
        id="chunk_semantic_refund",
        document_id="policy_semantic_refund",
        text="Refund delay SLA policy for pending refunds after an accepted return.",
        metadata={"case_type": "refund_delay", "refund_sla_days": 3},
        embedding=embedding_model.embed(query),
    )
    weak_chunk = DocumentChunk(
        id="chunk_semantic_weak",
        document_id="policy_semantic_weak",
        text="Generic support policy for unrelated account notifications.",
        metadata={"case_type": "refund_delay", "refund_sla_days": 3},
        embedding=[0.0] * embedding_model.dimensions,
    )
    policies = [
        PolicyDocument(
            id="policy_semantic_weak",
            title="Generic Support Policy",
            version="2026.07",
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            chunks=[weak_chunk],
        ),
        PolicyDocument(
            id="policy_semantic_refund",
            title="Refund SLA Policy",
            version="2026.07",
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            chunks=[expected_chunk],
        ),
    ]

    result = PolicyRetrievalService().retrieve_active_refund_policy(support_case, policies)

    assert result.chunk is not None
    assert result.chunk.id == "chunk_semantic_refund"
    assert result.citation is not None
    assert result.citation.chunk_id == "chunk_semantic_refund"
    assert result.retrieval_run.matched_chunk_ids[0] == "chunk_semantic_refund"


def test_policy_version_filter_rejects_other_active_versions():
    embedding_model = DeterministicEmbeddingModel()
    support_case = SupportCase(
        id="case_version_filter",
        case_type="refund_delay",
        policy_version="2026.07",
        status=CaseStatus.OPEN,
        order_id="order_version_filter",
        customer_id_masked="cust_***_version",
        customer_message="My refund is delayed.",
        created_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )
    current_chunk = DocumentChunk(
        id="chunk_current_version",
        document_id="policy_current_version",
        text="Current refund delay SLA is 3 days.",
        metadata={"case_type": "refund_delay", "refund_sla_days": 3},
        embedding=embedding_model.embed("Current refund delay SLA is 3 days."),
    )
    older_chunk = DocumentChunk(
        id="chunk_other_active_version",
        document_id="policy_other_active_version",
        text="Other active refund policy version says 9 days.",
        metadata={"case_type": "refund_delay", "refund_sla_days": 9},
        embedding=embedding_model.embed("Other active refund policy version says 9 days."),
    )
    policies = [
        PolicyDocument(
            id="policy_other_active_version",
            title="Other Active Refund Policy",
            version="2026.06",
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            chunks=[older_chunk],
        ),
        PolicyDocument(
            id="policy_current_version",
            title="Current Refund Policy",
            version="2026.07",
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            chunks=[current_chunk],
        ),
    ]

    result = PolicyRetrievalService().retrieve_active_refund_policy(support_case, policies)

    assert result.chunk is not None
    assert result.chunk.id == "chunk_current_version"
    assert result.retrieval_run.matched_chunk_ids == ["chunk_current_version"]
    assert "policy_other_active_version" in result.retrieval_run.rejected_policy_ids


def test_expired_policy_is_rejected(demo_store):
    support_case = demo_store.get_case("case_refund_delay_expired_policy")

    result = PolicyRetrievalService().retrieve_active_refund_policy(
        support_case, demo_store.list_policies()
    )

    assert result.chunk is None
    assert result.citation is None
    assert result.citations == []
    assert result.retrieval_run.status == "policy_missing"
    assert "policy_refund_2025" in result.retrieval_run.rejected_policy_ids


def test_policy_conflict_returns_conflict_without_choosing_one_policy(demo_store):
    support_case = demo_store.get_case("case_refund_delay_policy_conflict")

    result = PolicyRetrievalService().retrieve_active_refund_policy(
        support_case, demo_store.list_policies()
    )

    assert result.chunk is None
    assert result.citation is None
    assert result.has_conflict is True
    assert result.retrieval_run.status == "policy_conflict"
    assert set(result.retrieval_run.conflict_policy_ids) == {
        "policy_refund_conflict_short_sla",
        "policy_refund_conflict_long_sla",
    }
    assert {citation.chunk_id for citation in result.citations} == {
        "chunk_conflict_refund_sla_3_days",
        "chunk_conflict_refund_sla_7_days",
    }


def test_missing_refund_record_requires_human_review(investigation_service):
    packet = investigation_service.run("case_refund_delay_missing_evidence")

    assert packet.recommended_action == RecommendedAction.REQUEST_MORE_INFO
    assert packet.automation_decision == AutomationDecision.MANUAL_REVIEW_REQUIRED
    assert packet.automation_blockers == ["missing_refund_request"]
    assert packet.citations
    assert packet.retrieval_run.status == "policy_retrieved"
    assert packet.readiness.status == CaseReadinessStatus.MISSING_EVIDENCE
    assert packet.customer_response_allowed is False
    assert packet.requires_human_review is True


def test_sla_breach_requires_manual_review(investigation_service):
    packet = investigation_service.run("case_refund_delay_001")

    assert packet.recommended_action == RecommendedAction.ESCALATE
    assert packet.automation_decision == AutomationDecision.MANUAL_REVIEW_REQUIRED
    assert "sla_breached_operator_review_required" in packet.automation_blockers
    assert packet.citations
    assert packet.retrieval_run.status == "policy_retrieved"
    assert packet.readiness.status == CaseReadinessStatus.READY
    assert packet.customer_response_allowed is False
    assert packet.requires_human_review is True


def test_completed_refund_becomes_auto_resolve_candidate(investigation_service):
    packet = investigation_service.run("case_refund_delay_002")

    assert packet.recommended_action == RecommendedAction.RESOLVE
    assert packet.automation_decision == AutomationDecision.AUTO_RESOLVE_CANDIDATE
    assert packet.automation_blockers == []
    assert packet.citations
    assert packet.retrieval_run.status == "policy_retrieved"
    assert packet.readiness.status == CaseReadinessStatus.READY
    assert packet.customer_response_allowed is True
    assert packet.requires_human_review is False


def test_bad_provider_output_blocks_auto_resolution_and_customer_response(demo_store):
    service = InvestigationService(store=demo_store, provider=FakeProvider(mode="bad_output"))

    packet = service.run("case_refund_delay_002")

    assert packet.recommended_action == RecommendedAction.RESOLVE
    assert packet.automation_decision == AutomationDecision.MANUAL_REVIEW_REQUIRED
    assert "unsafe_provider_output" in packet.automation_blockers
    assert "provider_made_final_promise" in packet.automation_blockers
    assert packet.citations
    assert packet.retrieval_run.status == "policy_retrieved"
    assert packet.readiness.status == CaseReadinessStatus.READY
    assert packet.customer_response_allowed is False
    assert packet.requires_human_review is True


def test_response_without_citation_is_not_customer_facing(investigation_service):
    packet = investigation_service.run("case_refund_delay_expired_policy")

    assert packet.recommended_action == RecommendedAction.REQUEST_MORE_INFO
    assert packet.automation_decision == AutomationDecision.MANUAL_REVIEW_REQUIRED
    assert packet.automation_blockers == ["missing_active_policy"]
    assert packet.citations == []
    assert packet.retrieval_run.status == "policy_missing"
    assert packet.readiness.status == CaseReadinessStatus.MISSING_EVIDENCE
    assert packet.customer_response_allowed is False
    assert packet.requires_human_review is True


def test_policy_conflict_requires_human_review(investigation_service):
    packet = investigation_service.run("case_refund_delay_policy_conflict")

    assert packet.recommended_action == RecommendedAction.REQUEST_MORE_INFO
    assert packet.automation_decision == AutomationDecision.MANUAL_REVIEW_REQUIRED
    assert packet.automation_blockers == ["policy_conflict"]
    assert len(packet.citations) == 2
    assert packet.retrieval_run.status == "policy_conflict"
    assert packet.readiness.status == CaseReadinessStatus.POLICY_CONFLICT
    assert packet.customer_response_allowed is False
    assert packet.requires_human_review is True


def test_demo_evaluation_report_passes_all_golden_cases(investigation_service):
    report = run_demo_evaluation(investigation_service)

    assert report.total_cases == 5
    assert report.passed_cases == 5
    assert report.action_accuracy == 1.0
    assert report.citation_coverage == 1.0
    assert report.abstention_accuracy == 1.0
    assert all(result.passed for result in report.results)
