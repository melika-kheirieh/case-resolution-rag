from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.models import DocumentChunk, PolicyDocument
from app.services.embeddings import DeterministicEmbeddingModel, cosine_similarity


@dataclass(frozen=True)
class PolicyChunkMatch:
    policy: PolicyDocument
    chunk: DocumentChunk
    score: float


@dataclass(frozen=True)
class PolicyVectorSearchResult:
    matches: list[PolicyChunkMatch]
    rejected_policy_ids: list[str]


class PolicyVectorStore(Protocol):
    def search(
        self,
        *,
        query: str,
        case_type: str,
        effective_at: datetime,
        policy_version: str | None,
        top_k: int,
    ) -> PolicyVectorSearchResult:
        ...


class InMemoryPolicyVectorStore:
    def __init__(
        self,
        policies: list[PolicyDocument],
        embedding_model: DeterministicEmbeddingModel | None = None,
    ) -> None:
        self.policies = policies
        self.embedding_model = embedding_model or DeterministicEmbeddingModel()

    def search(
        self,
        *,
        query: str,
        case_type: str,
        effective_at: datetime,
        policy_version: str | None,
        top_k: int,
    ) -> PolicyVectorSearchResult:
        query_embedding = self.embedding_model.embed(query)
        matches: list[PolicyChunkMatch] = []
        rejected_policy_ids: list[str] = []

        for policy in self.policies:
            if not _policy_has_case_type(policy, case_type):
                continue
            if not policy.is_active_at(effective_at):
                rejected_policy_ids.append(policy.id)
                continue
            if policy_version is not None and policy.version != policy_version:
                rejected_policy_ids.append(policy.id)
                continue

            for chunk in policy.chunks:
                if chunk.metadata.get("case_type") != case_type:
                    continue
                embedding = chunk.embedding or self.embedding_model.embed(chunk.text)
                score = cosine_similarity(query_embedding, embedding)
                matches.append(PolicyChunkMatch(policy=policy, chunk=chunk, score=score))

        matches.sort(key=lambda match: match.score, reverse=True)
        return PolicyVectorSearchResult(
            matches=matches[:top_k],
            rejected_policy_ids=rejected_policy_ids,
        )


def _policy_has_case_type(policy: PolicyDocument, case_type: str) -> bool:
    return any(chunk.metadata.get("case_type") == case_type for chunk in policy.chunks)
