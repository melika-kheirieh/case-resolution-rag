from app.domain.models import PolicyDocument, RefundRequest, SupportCase, TimelineEvent


class DemoStore:
    def __init__(
        self,
        cases: dict[str, SupportCase],
        refunds_by_order_id: dict[str, RefundRequest],
        events_by_order_id: dict[str, list[TimelineEvent]],
        policies: list[PolicyDocument],
    ) -> None:
        self._cases = cases
        self._refunds_by_order_id = refunds_by_order_id
        self._events_by_order_id = events_by_order_id
        self._policies = policies

    def get_case(self, case_id: str) -> SupportCase:
        return self._cases[case_id]

    def list_cases(self) -> list[SupportCase]:
        return list(self._cases.values())

    def get_refund_for_order(self, order_id: str) -> RefundRequest | None:
        return self._refunds_by_order_id.get(order_id)

    def get_events_for_order(self, order_id: str) -> list[TimelineEvent]:
        return list(self._events_by_order_id[order_id])

    def list_policies(self) -> list[PolicyDocument]:
        return list(self._policies)
