from dataclasses import dataclass

from app.domain.models import (
    AutomationDecision,
    CaseReadinessStatus,
    EvaluationCaseResult,
    EvaluationReport,
    RecommendedAction,
)
from app.services.investigation import InvestigationService


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    expected_action: RecommendedAction
    expected_decision: AutomationDecision
    expected_readiness: CaseReadinessStatus
    expects_citation: bool
    expects_abstention: bool


GOLDEN_CASES = [
    GoldenCase(
        case_id="case_refund_delay_002",
        expected_action=RecommendedAction.RESOLVE,
        expected_decision=AutomationDecision.AUTO_RESOLVE_CANDIDATE,
        expected_readiness=CaseReadinessStatus.READY,
        expects_citation=True,
        expects_abstention=False,
    ),
    GoldenCase(
        case_id="case_refund_delay_001",
        expected_action=RecommendedAction.ESCALATE,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.READY,
        expects_citation=True,
        expects_abstention=True,
    ),
    GoldenCase(
        case_id="case_refund_delay_missing_evidence",
        expected_action=RecommendedAction.REQUEST_MORE_INFO,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.MISSING_EVIDENCE,
        expects_citation=True,
        expects_abstention=True,
    ),
    GoldenCase(
        case_id="case_refund_delay_expired_policy",
        expected_action=RecommendedAction.REQUEST_MORE_INFO,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.MISSING_EVIDENCE,
        expects_citation=False,
        expects_abstention=True,
    ),
    GoldenCase(
        case_id="case_refund_delay_policy_conflict",
        expected_action=RecommendedAction.REQUEST_MORE_INFO,
        expected_decision=AutomationDecision.MANUAL_REVIEW_REQUIRED,
        expected_readiness=CaseReadinessStatus.POLICY_CONFLICT,
        expects_citation=True,
        expects_abstention=True,
    ),
]


def run_demo_evaluation(investigation_service: InvestigationService) -> EvaluationReport:
    results = []
    citation_checks = []
    abstention_checks = []

    for golden_case in GOLDEN_CASES:
        packet = investigation_service.run(golden_case.case_id)
        notes = []
        action_ok = packet.recommended_action == golden_case.expected_action
        decision_ok = packet.automation_decision == golden_case.expected_decision
        readiness_ok = packet.readiness.status == golden_case.expected_readiness
        citation_ok = bool(packet.citations) == golden_case.expects_citation
        abstained = packet.requires_human_review and not packet.customer_response_allowed
        abstention_ok = abstained == golden_case.expects_abstention

        if not action_ok:
            notes.append("action_mismatch")
        if not decision_ok:
            notes.append("decision_mismatch")
        if not readiness_ok:
            notes.append("readiness_mismatch")
        if not citation_ok:
            notes.append("citation_expectation_mismatch")
        if not abstention_ok:
            notes.append("abstention_mismatch")

        passed = action_ok and decision_ok and readiness_ok and citation_ok and abstention_ok
        citation_checks.append(citation_ok)
        abstention_checks.append(abstention_ok)
        results.append(
            EvaluationCaseResult(
                case_id=golden_case.case_id,
                expected_action=golden_case.expected_action,
                actual_action=packet.recommended_action,
                expected_decision=golden_case.expected_decision,
                actual_decision=packet.automation_decision,
                expected_readiness=golden_case.expected_readiness,
                actual_readiness=packet.readiness.status,
                passed=passed,
                notes=notes,
            )
        )

    passed_cases = sum(result.passed for result in results)
    action_correct = sum(
        result.expected_action == result.actual_action for result in results
    )
    return EvaluationReport(
        total_cases=len(results),
        passed_cases=passed_cases,
        action_accuracy=action_correct / len(results),
        citation_coverage=sum(citation_checks) / len(citation_checks),
        abstention_accuracy=sum(abstention_checks) / len(abstention_checks),
        results=results,
    )
