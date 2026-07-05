from __future__ import annotations

import os

from app.services.audit_repository import InvestigationAuditRepository


DEFAULT_AUDIT_DATABASE_URL = "sqlite:///./case_resolution_audit.db"


def build_investigation_audit_repository() -> InvestigationAuditRepository:
    database_url = os.getenv("AUDIT_DATABASE_URL") or os.getenv("DATABASE_URL")
    repository = InvestigationAuditRepository(
        database_url=_to_sqlalchemy_url(database_url or DEFAULT_AUDIT_DATABASE_URL)
    )
    repository.ensure_schema()
    return repository


def _to_sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url
