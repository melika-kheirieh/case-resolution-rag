from typing import Literal

from app.domain.models import CustomerResponseDraft, RecommendedAction, SupportCase


class FakeProvider:
    name = "fake-provider"

    def __init__(self, mode: Literal["safe", "bad_output"] = "safe") -> None:
        self.mode = mode

    def draft_customer_response(
        self, support_case: SupportCase, action: RecommendedAction
    ) -> CustomerResponseDraft:
        if self.mode == "bad_output":
            return CustomerResponseDraft(
                text=(
                    "Your refund is guaranteed today. This promise can be sent without "
                    "checking policy evidence."
                ),
                is_structured=False,
                contains_final_promise=True,
                safety_notes=[
                    "Provider output bypassed the expected response contract.",
                    "Provider output made a final customer-facing promise.",
                ],
            )

        if action == RecommendedAction.ESCALATE:
            return CustomerResponseDraft(
                text=(
                    "We checked your return and refund timeline. Your refund is still pending "
                    "longer than the current review window, so we are escalating it for an "
                    "operator review. We will avoid making a final promise until that review "
                    "confirms the next step."
                )
            )

        if action == RecommendedAction.REQUEST_MORE_INFO:
            return CustomerResponseDraft(
                text=(
                    "We need one more check before we can give a reliable update on this refund. "
                    "Our support team will review the missing information and follow up."
                )
            )

        if action == RecommendedAction.RESOLVE:
            return CustomerResponseDraft(
                text=(
                    "We checked your return and refund timeline. The refund record shows the "
                    "refund has been completed, so this case can be closed unless you still "
                    "see a mismatch in your payment account."
                )
            )

        return CustomerResponseDraft(
            text=(
                "We checked the current refund timeline. The case is still within the expected "
                "review window, and we will keep monitoring it."
            )
        )
