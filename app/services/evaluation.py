from dataclasses import dataclass
from typing import Literal

from app.domain.models import (
    AutomationDecision,
    CaseReadinessStatus,
    EvaluationCaseResult,
    EvaluationReport,
    RecommendedAction,
)
from app.services.investigation import InvestigationService
from app.services.provider import FakeProvider


@dataclass(frozen=True)
class GoldenCase:
    scenario_id: str
    case_id: str
    provider_mode: Literal["safe", "bad_output"]
    expected_action: RecommendedAction
    expected_decision: AutomationDecision
    expected_readiness: CaseReadinessStatus
    expects_retrieval_hit: bool
    expects_citation: bool
    expects_manual_review: bool
    expects_abstention: bool
    expects_unsafe_response_blocked: bool = False


GOLDEN_CASES = [
    GoldenCase(
        scenario_id="auto_resolution_candidate",
        case_id="case_refund_delay_002",
        provider_mode="safe",
        expected_action=RecommendedAction.RESOLVE,
        expected_decision=AutomationDecision.AUTO_RESOLVE_CANDIDATE,
        expected_readiness=CaseReadinessStatus.READY,
        expects_retrieval_hit=True,
        expects_citation=True,
        expects_manual_review=False,
        expects_abstention=False,
    ),
    GoldenCase(
        scenario_id="sla_breach",
        case_id="case_refund_delay_001",
        provider_mode="safe",
        expected_action=RecommendedAction.ESCALATE,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.READY,
        expects_retrieval_hit=True,
        expects_citation=True,
        expects_manual_review=True,
        expects_abstention=True,
    ),
    GoldenCase(
        scenario_id="missing_evidence",
        case_id="case_refund_delay_missing_evidence",
        provider_mode="safe",
        expected_action=RecommendedAction.REQUEST_MORE_INFO,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.MISSING_EVIDENCE,
        expects_retrieval_hit=True,
        expects_citation=True,
        expects_manual_review=True,
        expects_abstention=True,
    ),
    GoldenCase(
        scenario_id="expired_policy",
        case_id="case_refund_delay_expired_policy",
        provider_mode="safe",
        expected_action=RecommendedAction.REQUEST_MORE_INFO,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.MISSING_EVIDENCE,
        expects_retrieval_hit=False,
        expects_citation=False,
        expects_manual_review=True,
        expects_abstention=True,
    ),
    GoldenCase(
        scenario_id="policy_conflict",
        case_id="case_refund_delay_policy_conflict",
        provider_mode="safe",
        expected_action=RecommendedAction.REQUEST_MORE_INFO,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.POLICY_CONFLICT,
        expects_retrieval_hit=True,
        expects_citation=True,
        expects_manual_review=True,
        expects_abstention=True,
    ),
    GoldenCase(
        scenario_id="refund_failed",
        case_id="case_refund_delay_refund_failed",
        provider_mode="safe",
        expected_action=RecommendedAction.ESCALATE,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.READY,
        expects_retrieval_hit=True,
        expects_citation=True,
        expects_manual_review=True,
        expects_abstention=True,
    ),
    GoldenCase(
        scenario_id="within_sla_wait",
        case_id="case_refund_delay_within_sla",
        provider_mode="safe",
        expected_action=RecommendedAction.WAIT,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.READY,
        expects_retrieval_hit=True,
        expects_citation=True,
        expects_manual_review=True,
        expects_abstention=True,
    ),
    GoldenCase(
        scenario_id="policy_version_mismatch",
        case_id="case_refund_delay_policy_version_mismatch",
        provider_mode="safe",
        expected_action=RecommendedAction.REQUEST_MORE_INFO,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.MISSING_EVIDENCE,
        expects_retrieval_hit=False,
        expects_citation=False,
        expects_manual_review=True,
        expects_abstention=True,
    ),
    GoldenCase(
        scenario_id="bad_ai_response",
        case_id="case_refund_delay_002",
        provider_mode="bad_output",
        expected_action=RecommendedAction.RESOLVE,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.READY,
        expects_retrieval_hit=True,
        expects_citation=True,
        expects_manual_review=True,
        expects_abstention=True,
        expects_unsafe_response_blocked=True,
    ),
]


def run_demo_evaluation(investigation_service: InvestigationService) -> EvaluationReport:
    results = []
    action_checks = []
    decision_checks = []
    retrieval_checks = []
    citation_checks = []
    manual_review_checks = []
    unsafe_response_checks = []
    abstention_checks = []

    for golden_case in GOLDEN_CASES:
        service = _service_for_golden_case(investigation_service, golden_case)
        packet = service.run(golden_case.case_id)
        notes = []
        action_ok = packet.recommended_action == golden_case.expected_action
        decision_ok = packet.automation_decision == golden_case.expected_decision
        readiness_ok = packet.readiness.status == golden_case.expected_readiness
        retrieval_hit = bool(packet.retrieval_run.matched_chunk_ids)
        retrieval_ok = retrieval_hit == golden_case.expects_retrieval_hit
        citation_present = bool(packet.citations)
        citation_ok = citation_present == golden_case.expects_citation
        manual_review = packet.requires_human_review
        manual_review_ok = manual_review == golden_case.expects_manual_review
        unsafe_response_blocked = (
            "unsafe_provider_output" in packet.automation_blockers
            and "provider_made_final_promise" in packet.automation_blockers
            and not packet.customer_response_allowed
        )
        unsafe_response_ok = (
            unsafe_response_blocked == golden_case.expects_unsafe_response_blocked
        )
        abstained = packet.requires_human_review and not packet.customer_response_allowed
        abstention_ok = abstained == golden_case.expects_abstention

        if not action_ok:
            notes.append("action_mismatch")
        if not decision_ok:
            notes.append("decision_mismatch")
        if not readiness_ok:
            notes.append("readiness_mismatch")
        if not retrieval_ok:
            notes.append("retrieval_hit_mismatch")
        if not citation_ok:
            notes.append("citation_expectation_mismatch")
        if not manual_review_ok:
            notes.append("manual_review_mismatch")
        if not unsafe_response_ok:
            notes.append("unsafe_response_block_mismatch")
        if not abstention_ok:
            notes.append("abstention_mismatch")

        passed = (
            action_ok
            and decision_ok
            and readiness_ok
            and retrieval_ok
            and citation_ok
            and manual_review_ok
            and unsafe_response_ok
            and abstention_ok
        )
        action_checks.append(action_ok)
        decision_checks.append(decision_ok)
        retrieval_checks.append(retrieval_ok)
        citation_checks.append(citation_ok)
        manual_review_checks.append(manual_review_ok)
        unsafe_response_checks.append(unsafe_response_ok)
        abstention_checks.append(abstention_ok)
        results.append(
            EvaluationCaseResult(
                scenario_id=golden_case.scenario_id,
                case_id=golden_case.case_id,
                provider_mode=golden_case.provider_mode,
                expected_action=golden_case.expected_action,
                actual_action=packet.recommended_action,
                expected_decision=golden_case.expected_decision,
                actual_decision=packet.automation_decision,
                expected_readiness=golden_case.expected_readiness,
                actual_readiness=packet.readiness.status,
                expected_retrieval_hit=golden_case.expects_retrieval_hit,
                actual_retrieval_hit=retrieval_hit,
                expected_citation_present=golden_case.expects_citation,
                actual_citation_present=citation_present,
                expected_manual_review=golden_case.expects_manual_review,
                actual_manual_review=manual_review,
                expected_unsafe_response_blocked=golden_case.expects_unsafe_response_blocked,
                actual_unsafe_response_blocked=unsafe_response_blocked,
                passed=passed,
                notes=notes,
            )
        )

    passed_cases = sum(result.passed for result in results)
    return EvaluationReport(
        total_cases=len(results),
        passed_cases=passed_cases,
        action_accuracy=_rate(action_checks),
        decision_accuracy=_rate(decision_checks),
        retrieval_hit_rate=_rate(retrieval_checks),
        citation_coverage=_rate(citation_checks),
        manual_review_accuracy=_rate(manual_review_checks),
        unsafe_response_block_rate=_rate(unsafe_response_checks),
        abstention_accuracy=_rate(abstention_checks),
        results=results,
    )


def _service_for_golden_case(
    investigation_service: InvestigationService,
    golden_case: GoldenCase,
) -> InvestigationService:
    if golden_case.provider_mode == "bad_output":
        return InvestigationService(
            store=investigation_service.store,
            policy_retrieval=investigation_service.policy_retrieval,
            provider=FakeProvider(mode="bad_output"),
        )
    return investigation_service


def _rate(checks: list[bool]) -> float:
    if not checks:
        return 1.0
    return sum(checks) / len(checks)
