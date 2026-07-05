from __future__ import annotations

from datetime import datetime
import json

from app.domain.models import DocumentChunk, PolicyDocument
from app.services.embeddings import DeterministicEmbeddingModel
from app.services.policy_vector_store import (
    PolicyChunkMatch,
    PolicyVectorSearchResult,
    PolicyVectorStore,
)


class PostgresPolicyVectorStore(PolicyVectorStore):
    def __init__(
        self,
        database_url: str,
        embedding_model: DeterministicEmbeddingModel | None = None,
    ) -> None:
        self.database_url = database_url
        self.embedding_model = embedding_model or DeterministicEmbeddingModel()

    def ensure_schema(self) -> None:
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS policy_chunks (
                    chunk_id text PRIMARY KEY,
                    document_id text NOT NULL,
                    title text NOT NULL,
                    version text NOT NULL,
                    effective_from timestamptz NOT NULL,
                    effective_to timestamptz,
                    case_type text NOT NULL,
                    text text NOT NULL,
                    metadata jsonb NOT NULL,
                    embedding vector({self.embedding_model.dimensions}) NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_policy_chunks_scope
                ON policy_chunks (case_type, version, effective_from, effective_to)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_policy_chunks_embedding
                ON policy_chunks USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 1)
                """
            )

    def replace_seed_policies(self, policies: list[PolicyDocument]) -> None:
        import psycopg

        rows = []
        for policy in policies:
            for chunk in policy.chunks:
                embedding = chunk.embedding or self.embedding_model.embed(chunk.text)
                rows.append(
                    (
                        chunk.id,
                        policy.id,
                        policy.title,
                        policy.version,
                        policy.effective_from,
                        policy.effective_to,
                        str(chunk.metadata["case_type"]),
                        chunk.text,
                        json.dumps(chunk.metadata),
                        _to_pgvector(embedding),
                    )
                )

        with psycopg.connect(self.database_url) as connection:
            connection.execute("DELETE FROM policy_chunks")
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO policy_chunks (
                        chunk_id,
                        document_id,
                        title,
                        version,
                        effective_from,
                        effective_to,
                        case_type,
                        text,
                        metadata,
                        embedding
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        document_id = EXCLUDED.document_id,
                        title = EXCLUDED.title,
                        version = EXCLUDED.version,
                        effective_from = EXCLUDED.effective_from,
                        effective_to = EXCLUDED.effective_to,
                        case_type = EXCLUDED.case_type,
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """,
                    rows,
                )

    def search(
        self,
        *,
        query: str,
        case_type: str,
        effective_at: datetime,
        policy_version: str | None,
        top_k: int,
    ) -> PolicyVectorSearchResult:
        import psycopg

        query_embedding = _to_pgvector(self.embedding_model.embed(query))
        version_filter = "AND version = %s" if policy_version is not None else ""
        version_params = (policy_version,) if policy_version is not None else ()
        version_rejection_filter = "OR version <> %s" if policy_version is not None else ""
        rejected_params = (
            (case_type, effective_at, effective_at, policy_version)
            if policy_version is not None
            else (case_type, effective_at, effective_at)
        )
        with psycopg.connect(self.database_url) as connection:
            active_rows = connection.execute(
                f"""
                SELECT
                    chunk_id,
                    document_id,
                    title,
                    version,
                    effective_from,
                    effective_to,
                    text,
                    metadata,
                    1 - (embedding <=> %s::vector) AS score
                FROM policy_chunks
                WHERE case_type = %s
                  {version_filter}
                  AND effective_from <= %s
                  AND (effective_to IS NULL OR %s < effective_to)
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    query_embedding,
                    case_type,
                    *version_params,
                    effective_at,
                    effective_at,
                    query_embedding,
                    top_k,
                ),
            ).fetchall()
            rejected_rows = connection.execute(
                f"""
                SELECT DISTINCT document_id
                FROM policy_chunks
                WHERE case_type = %s
                  AND (
                    NOT (effective_from <= %s AND (effective_to IS NULL OR %s < effective_to))
                    {version_rejection_filter}
                  )
                """,
                rejected_params,
            ).fetchall()

        return PolicyVectorSearchResult(
            matches=[
                PolicyChunkMatch(
                    policy=PolicyDocument(
                        id=row[1],
                        title=row[2],
                        version=row[3],
                        effective_from=row[4],
                        effective_to=row[5],
                        chunks=[],
                    ),
                    chunk=DocumentChunk(
                        id=row[0],
                        document_id=row[1],
                        text=row[6],
                        metadata=dict(row[7]),
                    ),
                    score=float(row[8]),
                )
                for row in active_rows
            ],
            rejected_policy_ids=[row[0] for row in rejected_rows],
        )


def _to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"
