import logging
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.models import (
    ActionValidationResult,
    AutomationDecision,
    CaseReadinessCheck,
    CaseReadinessStatus,
    ConfidenceLevel,
    CustomerResponseDraft,
    EvidenceRecord,
    InvestigationRun,
    RecommendedAction,
    ResolutionPacket,
    RefundRequest,
    RefundStatus,
    RiskGateResult,
    RiskLevel,
    SlaCheck,
)
from app.services.policy_retrieval import PolicyRetrievalService
from app.services.provider import FakeProvider
from app.services.store import DemoStore
from app.services.timeline import build_timeline
from app.services.logging_config import current_correlation_id, current_request_id
from app.services.audit_repository import InvestigationAuditRepository


logger = logging.getLogger(__name__)


class InvestigationService:
    def __init__(
        self,
        store: DemoStore,
        policy_retrieval: PolicyRetrievalService | None = None,
        provider: FakeProvider | None = None,
        audit_repository: InvestigationAuditRepository | None = None,
    ) -> None:
        self.store = store
        self.policy_retrieval = policy_retrieval or PolicyRetrievalService()
        self.provider = provider or FakeProvider()
        self.audit_repository = audit_repository

    def run(self, case_id: str) -> ResolutionPacket:
        request_id = current_request_id()
        correlation_id = current_correlation_id()
        support_case = self.store.get_case(case_id)
        refund = self.store.get_refund_for_order(support_case.order_id)
        timeline = build_timeline(self.store.get_events_for_order(support_case.order_id))
        retrieval_result = self.policy_retrieval.retrieve_active_refund_policy(
            support_case, self.store.list_policies()
        )
        policy_chunk = retrieval_result.chunk
        logger.info(
            "policy_retrieval_completed",
            extra={
                "case_id": support_case.id,
                "retrieved_chunk_ids": retrieval_result.retrieval_run.matched_chunk_ids,
                "retrieval_status": retrieval_result.retrieval_run.status,
            },
        )

        run = InvestigationRun(
            id=f"inv_{uuid4().hex[:12]}",
            case_id=support_case.id,
            provider_name=self.provider.name,
            created_at=datetime.now(tz=UTC),
            request_id=request_id,
            correlation_id=correlation_id,
            audit_events=[
                "case_loaded",
                f"timeline_built:{len(timeline)}_events",
                f"policy_retrieval:{retrieval_result.retrieval_run.status}",
            ],
        )

        blockers = self._check_evidence(
            refund=refund,
            has_policy=policy_chunk is not None,
            has_policy_conflict=retrieval_result.has_conflict,
        )
        run.audit_events.append(f"evidence_checked:{self._format_blockers(blockers)}")

        sla_days = int(policy_chunk.metadata["refund_sla_days"]) if policy_chunk else 0
        elapsed_days = (
            (support_case.created_at.date() - refund.requested_at.date()).days if refund else 0
        )
        sla_check = self._check_sla(
            elapsed_days=elapsed_days,
            sla_days=sla_days,
            has_policy=policy_chunk is not None,
            has_refund=refund is not None,
        )
        run.audit_events.append("sla_checked")

        if sla_check.is_breached:
            blockers.append("sla_breached_operator_review_required")
        if refund and refund.status == RefundStatus.FAILED:
            blockers.append("refund_failed_operator_review_required")

        validation = self._validate_action(
            refund=refund,
            sla_check=sla_check,
            has_policy=policy_chunk is not None,
            blockers=blockers,
        )
        run.audit_events.append("action_validated")

        customer_response_draft = self.provider.draft_customer_response(
            support_case=support_case,
            action=validation.action,
        )
        run.audit_events.append("response_generated")
        provider_blockers = self._provider_response_blockers(customer_response_draft)
        blockers.extend(provider_blockers)

        citations = retrieval_result.citations
        risk_gate = self._risk_gate(
            validation=validation,
            blockers=blockers,
            citations=citations,
        )
        run.audit_events.append(
            f"risk_gate:{risk_gate.risk_level}:passed={str(risk_gate.passed).lower()}"
        )
        automation_decision = self._automation_decision(risk_gate)
        run.audit_events.append(f"decision_created:{automation_decision}")
        customer_response_allowed = self._customer_response_allowed(
            automation_decision, citations, customer_response_draft
        )
        run.audit_events.append("customer_response_checked")
        logger.info(
            "investigation_decision_created",
            extra={
                "case_id": support_case.id,
                "decision": automation_decision,
                "blockers": blockers,
                "risk_level": risk_gate.risk_level,
                "risk_score": risk_gate.score,
            },
        )

        readiness = self._case_readiness(
            blockers=blockers,
            customer_response_allowed=customer_response_allowed,
        )
        run.audit_events.append(f"readiness_{readiness.status}")
        evidence = []
        if refund:
            evidence.append(
                EvidenceRecord(
                    source="refund_request",
                    record_id=refund.id,
                    description=f"Refund is {refund.status} for {refund.amount} {refund.currency}.",
                    observed_at=refund.updated_at,
                )
            )
        evidence.append(
            EvidenceRecord(
                source="support_case",
                record_id=support_case.id,
                description="Customer reported a delayed refund after return.",
                observed_at=support_case.created_at,
            )
        )

        limitations = []
        if not policy_chunk and not retrieval_result.has_conflict:
            limitations.append("No active refund policy was found for this case type.")
        if retrieval_result.has_conflict:
            limitations.append("Multiple active policy chunks disagree on the refund SLA.")
        if not refund:
            limitations.append("No refund request record is available for this order.")
        elif refund.status == RefundStatus.FAILED:
            reason = refund.failure_reason or "unknown"
            limitations.append(
                f"Refund failed with reason '{reason}', so an operator must verify the next step."
            )
        elif refund.status != RefundStatus.COMPLETED and refund.failure_reason is None:
            limitations.append("No refund failure reason is available yet.")
        if not customer_response_allowed:
            limitations.append(
                "Customer-facing response is blocked until policy evidence and decision checks pass."
            )
        limitations.extend(customer_response_draft.safety_notes)

        confidence = self._confidence_for_risk_gate(risk_gate)

        timeline_lines = [f"{event.happened_at.isoformat()} - {event.title}" for event in timeline]
        trace = [*run.audit_events, "packet_returned"]
        packet = ResolutionPacket(
            investigation_run_id=run.id,
            request_id=run.request_id,
            correlation_id=run.correlation_id,
            case_id=support_case.id,
            summary="Refund delay case for a returned e-commerce order.",
            timeline=timeline_lines,
            what_happened=timeline_lines,
            reconciliation_checks={
                "order_id": support_case.order_id,
                "refund_status": refund.status if refund else "missing",
                "refund_amount": str(refund.amount) if refund else "unknown",
                "sla": sla_check.reason,
            },
            evidence=evidence,
            citations=citations,
            retrieval_run=retrieval_result.retrieval_run,
            readiness=readiness,
            sla_check=sla_check,
            recommended_action=validation.action,
            risk_gate=risk_gate,
            automation_decision=automation_decision,
            automation_blockers=blockers,
            why_this_action=validation.reason,
            customer_safe_response=customer_response_draft.text,
            customer_response_allowed=customer_response_allowed,
            limitations=limitations,
            confidence=confidence,
            requires_human_review=automation_decision
            == AutomationDecision.MANUAL_REVIEW_REQUIRED,
            trace=trace,
            audit_reference=" > ".join(trace),
        )
        if self.audit_repository is not None:
            self.audit_repository.save(run=run, packet=packet)
        return packet

    def _check_evidence(
        self,
        refund: RefundRequest | None,
        has_policy: bool,
        has_policy_conflict: bool,
    ) -> list[str]:
        blockers = []
        if not refund:
            blockers.append("missing_refund_request")
        if has_policy_conflict:
            blockers.append("policy_conflict")
        elif not has_policy:
            blockers.append("missing_active_policy")
        return blockers

    def _check_sla(
        self, elapsed_days: int, sla_days: int, has_policy: bool, has_refund: bool
    ) -> SlaCheck:
        if not has_refund:
            return SlaCheck(
                is_breached=False,
                sla_days=sla_days,
                elapsed_days=0,
                reason="SLA cannot be checked without a refund request record.",
            )

        if not has_policy:
            return SlaCheck(
                is_breached=False,
                sla_days=0,
                elapsed_days=elapsed_days,
                reason="SLA cannot be checked without an active policy.",
            )

        is_breached = elapsed_days > sla_days
        reason = (
            f"Refund has been pending for {elapsed_days} days, above the {sla_days}-day SLA."
            if is_breached
            else f"Refund has been pending for {elapsed_days} days within the {sla_days}-day SLA."
        )
        return SlaCheck(
            is_breached=is_breached,
            sla_days=sla_days,
            elapsed_days=elapsed_days,
            reason=reason,
        )

    def _validate_action(
        self,
        refund: RefundRequest | None,
        sla_check: SlaCheck,
        has_policy: bool,
        blockers: list[str],
    ) -> ActionValidationResult:
        missing_required_context = {
            "missing_refund_request",
            "missing_active_policy",
            "policy_conflict",
        }.intersection(blockers)
        if missing_required_context:
            return ActionValidationResult(
                is_valid=True,
                action=RecommendedAction.REQUEST_MORE_INFO,
                reason="Missing or conflicting policy/refund evidence prevents an automated decision.",
            )

        if not has_policy:
            return ActionValidationResult(
                is_valid=True,
                action=RecommendedAction.REQUEST_MORE_INFO,
                reason="Missing active policy prevents a confident decision.",
            )

        if refund and refund.status == RefundStatus.COMPLETED:
            return ActionValidationResult(
                is_valid=True,
                action=RecommendedAction.RESOLVE,
                reason="Refund is completed and active policy evidence supports auto-resolution.",
            )

        if refund and refund.status == RefundStatus.FAILED:
            return ActionValidationResult(
                is_valid=True,
                action=RecommendedAction.ESCALATE,
                reason="Refund failed, so an operator must verify retry or compensation handling.",
            )

        if refund and sla_check.is_breached:
            return ActionValidationResult(
                is_valid=True,
                action=RecommendedAction.ESCALATE,
                reason="SLA is breached, so the case needs operator review before final response.",
            )

        return ActionValidationResult(
            is_valid=True,
            action=RecommendedAction.WAIT,
            reason="Refund is still inside the active policy SLA window.",
        )

    def _automation_decision(
        self,
        risk_gate: RiskGateResult,
    ) -> AutomationDecision:
        if risk_gate.passed:
            return AutomationDecision.AUTO_RESOLVE_CANDIDATE
        return AutomationDecision.MANUAL_REVIEW_REQUIRED

    def _risk_gate(
        self,
        validation: ActionValidationResult,
        blockers: list[str],
        citations: list[object],
    ) -> RiskGateResult:
        score = 0
        reasons: list[str] = []

        if blockers:
            score += 50
            reasons.extend(blockers)
        if not citations:
            score += 35
            reasons.append("missing_policy_citation")
        if validation.action != RecommendedAction.RESOLVE:
            score += 20
            reasons.append(f"action_requires_review:{validation.action}")

        risk_level = RiskLevel.LOW
        if score >= 50:
            risk_level = RiskLevel.HIGH
        elif score > 20:
            risk_level = RiskLevel.MEDIUM

        return RiskGateResult(
            passed=(
                validation.action == RecommendedAction.RESOLVE
                and score <= 20
                and not blockers
                and bool(citations)
            ),
            risk_level=risk_level,
            score=score,
            reasons=reasons,
        )

    def _confidence_for_risk_gate(self, risk_gate: RiskGateResult) -> ConfidenceLevel:
        if risk_gate.passed:
            return ConfidenceLevel.HIGH
        if risk_gate.risk_level == RiskLevel.HIGH:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.MEDIUM

    def _customer_response_allowed(
        self,
        automation_decision: AutomationDecision,
        citations: list[object],
        customer_response_draft: CustomerResponseDraft,
    ) -> bool:
        return (
            automation_decision == AutomationDecision.AUTO_RESOLVE_CANDIDATE
            and bool(citations)
            and getattr(customer_response_draft, "is_structured", False)
            and not getattr(customer_response_draft, "contains_final_promise", True)
        )

    def _provider_response_blockers(
        self, customer_response_draft: CustomerResponseDraft
    ) -> list[str]:
        blockers = []
        if not getattr(customer_response_draft, "is_structured", False):
            blockers.append("unsafe_provider_output")
        if getattr(customer_response_draft, "contains_final_promise", True):
            blockers.append("provider_made_final_promise")
        return blockers

    def _case_readiness(
        self,
        blockers: list[str],
        customer_response_allowed: bool,
    ) -> CaseReadinessCheck:
        if "policy_conflict" in blockers:
            return CaseReadinessCheck(
                status=CaseReadinessStatus.POLICY_CONFLICT,
                reasons=blockers,
                can_generate_customer_response=customer_response_allowed,
            )
        if {"missing_refund_request", "missing_active_policy"}.intersection(blockers):
            return CaseReadinessCheck(
                status=CaseReadinessStatus.MISSING_EVIDENCE,
                reasons=blockers,
                can_generate_customer_response=customer_response_allowed,
            )
        return CaseReadinessCheck(
            status=CaseReadinessStatus.READY,
            reasons=blockers,
            can_generate_customer_response=customer_response_allowed,
        )

    def _format_blockers(self, blockers: list[str]) -> str:
        return ",".join(blockers) if blockers else "none"
