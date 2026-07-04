from datetime import UTC, datetime
from uuid import uuid4

from app.domain.models import Citation, PolicyDocument, PolicyRetrievalResult, RetrievalRun, SupportCase


class PolicyRetrievalService:
    def retrieve_active_refund_policy(
        self, support_case: SupportCase, policies: list[PolicyDocument]
    ) -> PolicyRetrievalResult:
        active_policies = []
        rejected_policy_ids = []
        for policy in policies:
            if policy.is_active_at(support_case.created_at):
                active_policies.append(policy)
            else:
                rejected_policy_ids.append(policy.id)

        matches = []
        for policy in active_policies:
            for chunk in policy.chunks:
                if chunk.metadata.get("case_type") == support_case.case_type:
                    matches.append((policy, chunk))

        citations = [
            Citation(
                chunk_id=chunk.id,
                document_id=policy.id,
                title=f"{policy.title} v{policy.version}",
                excerpt=chunk.text,
            )
            for policy, chunk in matches
        ]
        matched_chunk_ids = [chunk.id for _, chunk in matches]
        sla_values = {
            chunk.metadata.get("refund_sla_days")
            for _, chunk in matches
            if chunk.metadata.get("refund_sla_days") is not None
        }
        has_conflict = len(matches) > 1 and len(sla_values) > 1
        status = "policy_conflict" if has_conflict else "policy_retrieved" if matches else "policy_missing"
        conflict_policy_ids = [policy.id for policy, _ in matches] if has_conflict else []
        retrieval_run = RetrievalRun(
            id=f"ret_{uuid4().hex[:12]}",
            case_id=support_case.id,
            case_type=support_case.case_type,
            matched_chunk_ids=matched_chunk_ids,
            rejected_policy_ids=rejected_policy_ids,
            conflict_policy_ids=conflict_policy_ids,
            status=status,
            created_at=datetime.now(tz=UTC),
        )

        if has_conflict or not matches:
            return PolicyRetrievalResult(
                chunk=None,
                citation=None,
                citations=citations,
                retrieval_run=retrieval_run,
                has_conflict=has_conflict,
            )

        policy, chunk = matches[0]
        citation = citations[0]
        return PolicyRetrievalResult(
            chunk=chunk,
            citation=citation,
            citations=[citation],
            retrieval_run=retrieval_run,
            has_conflict=False,
        )
