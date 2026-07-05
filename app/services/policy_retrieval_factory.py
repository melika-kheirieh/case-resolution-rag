from __future__ import annotations

import os

from app.domain.models import PolicyDocument
from app.services.pgvector_store import PostgresPolicyVectorStore
from app.services.policy_retrieval import PolicyRetrievalService


def build_policy_retrieval_service(policies: list[PolicyDocument]) -> PolicyRetrievalService:
    policy_store = os.getenv("POLICY_STORE", "inmemory")
    if policy_store == "postgres":
        database_url = os.environ["DATABASE_URL"]
        vector_store = PostgresPolicyVectorStore(database_url=database_url)
        vector_store.ensure_schema()
        vector_store.replace_seed_policies(policies)
        return PolicyRetrievalService(vector_store=vector_store)

    return PolicyRetrievalService()
