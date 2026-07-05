from datetime import UTC, datetime
from uuid import uuid4

from app.domain.models import Citation, PolicyDocument, PolicyRetrievalResult, RetrievalRun, SupportCase
from app.services.policy_vector_store import InMemoryPolicyVectorStore, PolicyVectorStore


class PolicyRetrievalService:
    def __init__(self, vector_store: PolicyVectorStore | None = None, top_k: int = 5) -> None:
        self.vector_store = vector_store
        self.top_k = top_k

    def retrieve_active_refund_policy(
        self, support_case: SupportCase, policies: list[PolicyDocument]
    ) -> PolicyRetrievalResult:
        vector_store = self.vector_store or InMemoryPolicyVectorStore(policies)
        search_result = vector_store.search(
            query=self._build_policy_query(support_case),
            case_type=support_case.case_type,
            effective_at=support_case.created_at,
            policy_version=support_case.policy_version,
            top_k=self.top_k,
        )
        matches = search_result.matches

        citations = [
            Citation(
                chunk_id=match.chunk.id,
                document_id=match.policy.id,
                title=f"{match.policy.title} v{match.policy.version}",
                excerpt=match.chunk.text,
            )
            for match in matches
        ]
        matched_chunk_ids = [match.chunk.id for match in matches]
        sla_values = {
            match.chunk.metadata.get("refund_sla_days")
            for match in matches
            if match.chunk.metadata.get("refund_sla_days") is not None
        }
        has_conflict = len(matches) > 1 and len(sla_values) > 1
        status = "policy_conflict" if has_conflict else "policy_retrieved" if matches else "policy_missing"
        conflict_policy_ids = [match.policy.id for match in matches] if has_conflict else []
        retrieval_run = RetrievalRun(
            id=f"ret_{uuid4().hex[:12]}",
            case_id=support_case.id,
            case_type=support_case.case_type,
            matched_chunk_ids=matched_chunk_ids,
            rejected_policy_ids=search_result.rejected_policy_ids,
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

        match = matches[0]
        citation = citations[0]
        return PolicyRetrievalResult(
            chunk=match.chunk,
            citation=citation,
            citations=[citation],
            retrieval_run=retrieval_run,
            has_conflict=False,
        )

    def _build_policy_query(self, support_case: SupportCase) -> str:
        return (
            f"{support_case.case_type} refund policy SLA evidence: "
            f"{support_case.customer_message}"
        )
