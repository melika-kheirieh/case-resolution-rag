from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CaseStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    WAITING = "waiting"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class RefundStatus(StrEnum):
    REQUESTED = "requested"
    PENDING = "pending"
    FAILED = "failed"
    COMPLETED = "completed"


class TimelineEventType(StrEnum):
    ORDER_PLACED = "order_placed"
    PAYMENT_CAPTURED = "payment_captured"
    RETURN_REQUESTED = "return_requested"
    REFUND_REQUESTED = "refund_requested"
    REFUND_PENDING = "refund_pending"
    REFUND_FAILED = "refund_failed"


class RecommendedAction(StrEnum):
    WAIT = "wait"
    ESCALATE = "escalate"
    REQUEST_MORE_INFO = "request_more_info"
    RESOLVE = "resolve"


class AutomationDecision(StrEnum):
    AUTO_RESOLVE_CANDIDATE = "auto_resolve_candidate"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CaseReadinessStatus(StrEnum):
    READY = "ready"
    MISSING_EVIDENCE = "missing_evidence"
    POLICY_CONFLICT = "policy_conflict"
    PERMISSION_LIMITED = "permission_limited"
    STALE_DATA = "stale_data"


class SupportCase(BaseModel):
    id: str
    case_type: str
    policy_version: str | None = None
    status: CaseStatus
    order_id: str
    customer_id_masked: str
    customer_message: str
    created_at: datetime


class OrderPayment(BaseModel):
    id: str
    order_id: str
    amount: int
    currency: str
    status: str
    captured_at: datetime


class RefundRequest(BaseModel):
    id: str
    order_id: str
    amount: int
    currency: str
    status: RefundStatus
    requested_at: datetime
    updated_at: datetime
    failure_reason: str | None = None


class TimelineEvent(BaseModel):
    type: TimelineEventType
    happened_at: datetime
    title: str
    details: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    id: str
    document_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] = Field(default_factory=list)


class PolicyDocument(BaseModel):
    id: str
    title: str
    version: str
    effective_from: datetime
    effective_to: datetime | None = None
    chunks: list[DocumentChunk]

    def is_active_at(self, moment: datetime) -> bool:
        starts_before = self.effective_from <= moment
        has_not_expired = self.effective_to is None or moment < self.effective_to
        return starts_before and has_not_expired


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    excerpt: str


class EvidenceRecord(BaseModel):
    source: str
    record_id: str
    description: str
    observed_at: datetime | None = None


class SlaCheck(BaseModel):
    is_breached: bool
    sla_days: int
    elapsed_days: int
    reason: str


class CaseReadinessCheck(BaseModel):
    status: CaseReadinessStatus
    reasons: list[str] = Field(default_factory=list)
    can_generate_customer_response: bool


class ActionValidationResult(BaseModel):
    is_valid: bool
    action: RecommendedAction
    reason: str


class RiskGateResult(BaseModel):
    passed: bool
    risk_level: RiskLevel
    score: int
    reasons: list[str] = Field(default_factory=list)


class CustomerResponseDraft(BaseModel):
    text: str
    is_structured: bool = True
    contains_final_promise: bool = False
    safety_notes: list[str] = Field(default_factory=list)


class InvestigationRun(BaseModel):
    id: str
    case_id: str
    provider_name: str
    created_at: datetime
    audit_events: list[str] = Field(default_factory=list)


class RetrievalRun(BaseModel):
    id: str
    case_id: str
    case_type: str
    matched_chunk_ids: list[str] = Field(default_factory=list)
    rejected_policy_ids: list[str] = Field(default_factory=list)
    conflict_policy_ids: list[str] = Field(default_factory=list)
    status: str
    created_at: datetime


class PolicyRetrievalResult(BaseModel):
    chunk: DocumentChunk | None
    citation: Citation | None
    citations: list[Citation] = Field(default_factory=list)
    retrieval_run: RetrievalRun
    has_conflict: bool = False


class EvaluationCaseResult(BaseModel):
    case_id: str
    expected_action: RecommendedAction
    actual_action: RecommendedAction
    expected_decision: AutomationDecision
    actual_decision: AutomationDecision
    expected_readiness: CaseReadinessStatus
    actual_readiness: CaseReadinessStatus
    passed: bool
    notes: list[str] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    total_cases: int
    passed_cases: int
    action_accuracy: float
    citation_coverage: float
    abstention_accuracy: float
    results: list[EvaluationCaseResult]


class ResolutionPacket(BaseModel):
    investigation_run_id: str
    case_id: str
    summary: str
    timeline: list[str]
    what_happened: list[str]
    reconciliation_checks: dict[str, str]
    evidence: list[EvidenceRecord]
    citations: list[Citation]
    retrieval_run: RetrievalRun
    readiness: CaseReadinessCheck
    sla_check: SlaCheck
    recommended_action: RecommendedAction
    risk_gate: RiskGateResult
    automation_decision: AutomationDecision
    automation_blockers: list[str]
    why_this_action: str
    customer_safe_response: str
    customer_response_allowed: bool
    limitations: list[str]
    confidence: ConfidenceLevel
    requires_human_review: bool
    trace: list[str]
    audit_reference: str
