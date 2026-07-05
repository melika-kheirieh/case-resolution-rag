from datetime import UTC, datetime

from app.domain.models import (
    CaseStatus,
    DocumentChunk,
    PolicyDocument,
    RefundRequest,
    RefundStatus,
    SupportCase,
    TimelineEvent,
    TimelineEventType,
)
from app.services.embeddings import DeterministicEmbeddingModel
from app.services.store import DemoStore


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


embedding_model = DeterministicEmbeddingModel()


def policy_chunk(
    *,
    id: str,
    document_id: str,
    text: str,
    metadata: dict[str, object],
) -> DocumentChunk:
    return DocumentChunk(
        id=id,
        document_id=document_id,
        text=text,
        metadata=metadata,
        embedding=embedding_model.embed(text),
    )


def build_demo_store() -> DemoStore:
    breached_case = SupportCase(
        id="case_refund_delay_001",
        case_type="refund_delay",
        policy_version="2026.06",
        status=CaseStatus.OPEN,
        order_id="order_1001",
        customer_id_masked="cust_***_4821",
        customer_message="I returned my item, but my refund is still pending.",
        created_at=dt("2026-07-01T09:30:00"),
    )

    completed_case = SupportCase(
        id="case_refund_delay_002",
        case_type="refund_delay",
        policy_version="2026.06",
        status=CaseStatus.OPEN,
        order_id="order_1002",
        customer_id_masked="cust_***_9910",
        customer_message="Can you confirm whether my refund was processed?",
        created_at=dt("2026-07-01T10:00:00"),
    )

    missing_evidence_case = SupportCase(
        id="case_refund_delay_missing_evidence",
        case_type="refund_delay",
        policy_version="2026.06",
        status=CaseStatus.OPEN,
        order_id="order_1003",
        customer_id_masked="cust_***_2271",
        customer_message="I returned the item, but I cannot see my refund.",
        created_at=dt("2026-07-01T11:00:00"),
    )

    expired_policy_case = SupportCase(
        id="case_refund_delay_expired_policy",
        case_type="refund_delay_legacy",
        policy_version="2025.12",
        status=CaseStatus.OPEN,
        order_id="order_1004",
        customer_id_masked="cust_***_7312",
        customer_message="My old refund case still has no answer.",
        created_at=dt("2026-07-01T12:00:00"),
    )

    policy_conflict_case = SupportCase(
        id="case_refund_delay_policy_conflict",
        case_type="refund_delay_conflict",
        status=CaseStatus.OPEN,
        order_id="order_1005",
        customer_id_masked="cust_***_1844",
        customer_message="The return was accepted, but two support notes show different refund windows.",
        created_at=dt("2026-07-01T13:00:00"),
    )

    refund_failed_case = SupportCase(
        id="case_refund_delay_refund_failed",
        case_type="refund_delay",
        policy_version="2026.06",
        status=CaseStatus.OPEN,
        order_id="order_1006",
        customer_id_masked="cust_***_6107",
        customer_message="The refund failed after my return was accepted. What happens next?",
        created_at=dt("2026-07-01T14:00:00"),
    )

    breached_refund = RefundRequest(
        id="refund_9001",
        order_id="order_1001",
        amount=129_00,
        currency="USD",
        status=RefundStatus.PENDING,
        requested_at=dt("2026-06-25T12:00:00"),
        updated_at=dt("2026-06-30T16:40:00"),
    )

    completed_refund = RefundRequest(
        id="refund_9002",
        order_id="order_1002",
        amount=89_00,
        currency="USD",
        status=RefundStatus.COMPLETED,
        requested_at=dt("2026-06-29T08:00:00"),
        updated_at=dt("2026-06-30T13:10:00"),
    )

    expired_policy_refund = RefundRequest(
        id="refund_9004",
        order_id="order_1004",
        amount=55_00,
        currency="USD",
        status=RefundStatus.PENDING,
        requested_at=dt("2026-06-20T09:00:00"),
        updated_at=dt("2026-06-30T17:30:00"),
    )

    policy_conflict_refund = RefundRequest(
        id="refund_9005",
        order_id="order_1005",
        amount=72_00,
        currency="USD",
        status=RefundStatus.PENDING,
        requested_at=dt("2026-06-28T09:00:00"),
        updated_at=dt("2026-06-30T18:00:00"),
    )

    failed_refund = RefundRequest(
        id="refund_9006",
        order_id="order_1006",
        amount=64_00,
        currency="USD",
        status=RefundStatus.FAILED,
        requested_at=dt("2026-06-29T09:00:00"),
        updated_at=dt("2026-06-30T10:35:00"),
        failure_reason="processor_rejected",
    )

    breached_events = [
        TimelineEvent(
            type=TimelineEventType.ORDER_PLACED,
            happened_at=dt("2026-06-18T10:15:00"),
            title="Order placed",
            details={"order_id": "order_1001", "amount": 129_00, "currency": "USD"},
        ),
        TimelineEvent(
            type=TimelineEventType.PAYMENT_CAPTURED,
            happened_at=dt("2026-06-18T10:16:00"),
            title="Payment captured",
            details={"payment_id": "pay_7001", "amount": 129_00, "currency": "USD"},
        ),
        TimelineEvent(
            type=TimelineEventType.RETURN_REQUESTED,
            happened_at=dt("2026-06-23T09:20:00"),
            title="Return requested",
            details={"return_id": "return_5001", "reason": "size_mismatch"},
        ),
        TimelineEvent(
            type=TimelineEventType.REFUND_REQUESTED,
            happened_at=breached_refund.requested_at,
            title="Refund requested",
            details={"refund_id": breached_refund.id, "amount": breached_refund.amount},
        ),
        TimelineEvent(
            type=TimelineEventType.REFUND_PENDING,
            happened_at=breached_refund.updated_at,
            title="Refund still pending",
            details={"refund_id": breached_refund.id, "status": breached_refund.status},
        ),
    ]

    completed_events = [
        TimelineEvent(
            type=TimelineEventType.ORDER_PLACED,
            happened_at=dt("2026-06-24T14:00:00"),
            title="Order placed",
            details={"order_id": "order_1002", "amount": 89_00, "currency": "USD"},
        ),
        TimelineEvent(
            type=TimelineEventType.RETURN_REQUESTED,
            happened_at=dt("2026-06-28T09:30:00"),
            title="Return requested",
            details={"return_id": "return_5002", "reason": "changed_mind"},
        ),
        TimelineEvent(
            type=TimelineEventType.REFUND_REQUESTED,
            happened_at=completed_refund.requested_at,
            title="Refund requested",
            details={"refund_id": completed_refund.id, "amount": completed_refund.amount},
        ),
    ]

    missing_evidence_events = [
        TimelineEvent(
            type=TimelineEventType.ORDER_PLACED,
            happened_at=dt("2026-06-27T10:10:00"),
            title="Order placed",
            details={"order_id": "order_1003", "amount": 44_00, "currency": "USD"},
        ),
        TimelineEvent(
            type=TimelineEventType.RETURN_REQUESTED,
            happened_at=dt("2026-06-30T09:10:00"),
            title="Return requested",
            details={"return_id": "return_5003", "reason": "damaged"},
        ),
    ]

    expired_policy_events = [
        TimelineEvent(
            type=TimelineEventType.ORDER_PLACED,
            happened_at=dt("2026-06-10T10:10:00"),
            title="Order placed",
            details={"order_id": "order_1004", "amount": 55_00, "currency": "USD"},
        ),
        TimelineEvent(
            type=TimelineEventType.REFUND_REQUESTED,
            happened_at=expired_policy_refund.requested_at,
            title="Refund requested",
            details={"refund_id": expired_policy_refund.id, "amount": expired_policy_refund.amount},
        ),
    ]

    policy_conflict_events = [
        TimelineEvent(
            type=TimelineEventType.ORDER_PLACED,
            happened_at=dt("2026-06-26T10:10:00"),
            title="Order placed",
            details={"order_id": "order_1005", "amount": 72_00, "currency": "USD"},
        ),
        TimelineEvent(
            type=TimelineEventType.RETURN_REQUESTED,
            happened_at=dt("2026-06-27T12:20:00"),
            title="Return requested",
            details={"return_id": "return_5005", "reason": "wrong_color"},
        ),
        TimelineEvent(
            type=TimelineEventType.REFUND_REQUESTED,
            happened_at=policy_conflict_refund.requested_at,
            title="Refund requested",
            details={
                "refund_id": policy_conflict_refund.id,
                "amount": policy_conflict_refund.amount,
            },
        ),
        TimelineEvent(
            type=TimelineEventType.REFUND_PENDING,
            happened_at=policy_conflict_refund.updated_at,
            title="Refund still pending",
            details={
                "refund_id": policy_conflict_refund.id,
                "status": policy_conflict_refund.status,
            },
        ),
    ]

    failed_refund_events = [
        TimelineEvent(
            type=TimelineEventType.ORDER_PLACED,
            happened_at=dt("2026-06-25T11:10:00"),
            title="Order placed",
            details={"order_id": "order_1006", "amount": 64_00, "currency": "USD"},
        ),
        TimelineEvent(
            type=TimelineEventType.PAYMENT_CAPTURED,
            happened_at=dt("2026-06-25T11:11:00"),
            title="Payment captured",
            details={"payment_id": "pay_7006", "amount": 64_00, "currency": "USD"},
        ),
        TimelineEvent(
            type=TimelineEventType.RETURN_REQUESTED,
            happened_at=dt("2026-06-28T12:15:00"),
            title="Return requested",
            details={"return_id": "return_5006", "reason": "defective"},
        ),
        TimelineEvent(
            type=TimelineEventType.REFUND_REQUESTED,
            happened_at=failed_refund.requested_at,
            title="Refund requested",
            details={"refund_id": failed_refund.id, "amount": failed_refund.amount},
        ),
        TimelineEvent(
            type=TimelineEventType.REFUND_FAILED,
            happened_at=failed_refund.updated_at,
            title="Refund failed",
            details={
                "refund_id": failed_refund.id,
                "status": failed_refund.status,
                "failure_reason": failed_refund.failure_reason,
            },
        ),
    ]

    active_policy = PolicyDocument(
        id="policy_refund_2026_summer",
        title="Refund and Return Policy",
        version="2026.06",
        effective_from=dt("2026-06-01T00:00:00"),
        effective_to=None,
        chunks=[
            policy_chunk(
                id="chunk_refund_sla",
                document_id="policy_refund_2026_summer",
                text=(
                    "Eligible refunds should move out of pending status within 3 calendar "
                    "days after refund request creation. Cases beyond this window require "
                    "operator review before any customer-facing promise is made. If the "
                    "refund is already completed and the timeline has enough evidence, "
                    "the case can be treated as an auto-resolution candidate."
                ),
                metadata={
                    "case_type": "refund_delay",
                    "market": "demo",
                    "channel": "web",
                    "refund_sla_days": 3,
                },
            )
        ],
    )

    expired_policy = PolicyDocument(
        id="policy_refund_2025",
        title="Expired Refund Policy",
        version="2025.12",
        effective_from=dt("2025-12-01T00:00:00"),
        effective_to=dt("2026-05-31T23:59:59"),
        chunks=[
            policy_chunk(
                id="chunk_expired_refund_sla",
                document_id="policy_refund_2025",
                text="Expired policy: refunds should be reviewed within 5 days.",
                metadata={"case_type": "refund_delay_legacy", "refund_sla_days": 5},
            )
        ],
    )

    conflict_policy_short_sla = PolicyDocument(
        id="policy_refund_conflict_short_sla",
        title="Refund Policy Conflict Demo",
        version="2026.07-a",
        effective_from=dt("2026-06-01T00:00:00"),
        effective_to=None,
        chunks=[
            policy_chunk(
                id="chunk_conflict_refund_sla_3_days",
                document_id="policy_refund_conflict_short_sla",
                text=(
                    "Conflict demo policy A: refund-delay conflict cases should be "
                    "reviewed if still pending after 3 calendar days."
                ),
                metadata={"case_type": "refund_delay_conflict", "refund_sla_days": 3},
            )
        ],
    )

    conflict_policy_long_sla = PolicyDocument(
        id="policy_refund_conflict_long_sla",
        title="Refund Policy Conflict Demo",
        version="2026.07-b",
        effective_from=dt("2026-06-01T00:00:00"),
        effective_to=None,
        chunks=[
            policy_chunk(
                id="chunk_conflict_refund_sla_7_days",
                document_id="policy_refund_conflict_long_sla",
                text=(
                    "Conflict demo policy B: refund-delay conflict cases should remain "
                    "inside the normal waiting window for 7 calendar days."
                ),
                metadata={"case_type": "refund_delay_conflict", "refund_sla_days": 7},
            )
        ],
    )

    return DemoStore(
        cases={
            breached_case.id: breached_case,
            completed_case.id: completed_case,
            missing_evidence_case.id: missing_evidence_case,
            expired_policy_case.id: expired_policy_case,
            policy_conflict_case.id: policy_conflict_case,
            refund_failed_case.id: refund_failed_case,
        },
        refunds_by_order_id={
            breached_case.order_id: breached_refund,
            completed_case.order_id: completed_refund,
            expired_policy_case.order_id: expired_policy_refund,
            policy_conflict_case.order_id: policy_conflict_refund,
            refund_failed_case.order_id: failed_refund,
        },
        events_by_order_id={
            breached_case.order_id: breached_events,
            completed_case.order_id: completed_events,
            missing_evidence_case.order_id: missing_evidence_events,
            expired_policy_case.order_id: expired_policy_events,
            policy_conflict_case.order_id: policy_conflict_events,
            refund_failed_case.order_id: failed_refund_events,
        },
        policies=[expired_policy, active_policy, conflict_policy_short_sla, conflict_policy_long_sla],
    )
