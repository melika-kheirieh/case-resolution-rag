from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.domain.models import (
    AutomationDecision,
    InvestigationRun,
    PersistedAuditEvent,
    PersistedInvestigationRun,
    RecommendedAction,
    ResolutionPacket,
    RiskLevel,
)


class Base(DeclarativeBase):
    pass


class InvestigationRunRow(Base):
    __tablename__ = "investigation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(128), index=True)
    provider_name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    recommended_action: Mapped[str] = mapped_column(String(64))
    automation_decision: Mapped[str] = mapped_column(String(64))
    risk_level: Mapped[str] = mapped_column(String(32))
    risk_score: Mapped[int] = mapped_column(Integer)
    customer_response_allowed: Mapped[bool] = mapped_column(Boolean)
    requires_human_review: Mapped[bool] = mapped_column(Boolean)
    audit_reference: Mapped[str] = mapped_column(Text)

    audit_events: Mapped[list[AuditEventRow]] = relationship(
        back_populates="investigation_run",
        cascade="all, delete-orphan",
        order_by="AuditEventRow.sequence_number",
    )


class AuditEventRow(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint(
            "investigation_run_id",
            "sequence_number",
            name="uq_audit_events_run_sequence",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_run_id: Mapped[str] = mapped_column(
        ForeignKey("investigation_runs.id", ondelete="CASCADE"),
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    investigation_run: Mapped[InvestigationRunRow] = relationship(
        back_populates="audit_events",
    )


class InvestigationAuditRepository:
    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, connect_args=connect_args)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    @classmethod
    def from_engine(cls, engine: Engine) -> InvestigationAuditRepository:
        repository = cls.__new__(cls)
        repository.engine = engine
        repository.session_factory = sessionmaker(engine, expire_on_commit=False)
        return repository

    def ensure_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def save(self, *, run: InvestigationRun, packet: ResolutionPacket) -> None:
        event_time = datetime.now(tz=UTC)
        with self.session_factory.begin() as session:
            session.add(
                InvestigationRunRow(
                    id=run.id,
                    case_id=run.case_id,
                    provider_name=run.provider_name,
                    created_at=run.created_at,
                    request_id=run.request_id,
                    correlation_id=run.correlation_id,
                    recommended_action=packet.recommended_action,
                    automation_decision=packet.automation_decision,
                    risk_level=packet.risk_gate.risk_level,
                    risk_score=packet.risk_gate.score,
                    customer_response_allowed=packet.customer_response_allowed,
                    requires_human_review=packet.requires_human_review,
                    audit_reference=packet.audit_reference,
                    audit_events=[
                        AuditEventRow(
                            sequence_number=sequence_number,
                            name=event_name,
                            created_at=event_time,
                        )
                        for sequence_number, event_name in enumerate(packet.trace, start=1)
                    ],
                )
            )

    def get(self, run_id: str) -> PersistedInvestigationRun | None:
        with self.session_factory() as session:
            row = session.get(InvestigationRunRow, run_id)
            if row is None:
                return None
            return _to_persisted_run(row)

    def list_recent(self, *, limit: int = 20) -> list[PersistedInvestigationRun]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(InvestigationRunRow)
                .order_by(InvestigationRunRow.created_at.desc())
                .limit(limit)
            ).all()
            return [_to_persisted_run(row) for row in rows]


def _to_persisted_run(row: InvestigationRunRow) -> PersistedInvestigationRun:
    return PersistedInvestigationRun(
        id=row.id,
        case_id=row.case_id,
        provider_name=row.provider_name,
        created_at=_as_utc(row.created_at),
        request_id=row.request_id,
        correlation_id=row.correlation_id,
        recommended_action=RecommendedAction(row.recommended_action),
        automation_decision=AutomationDecision(row.automation_decision),
        risk_level=RiskLevel(row.risk_level),
        risk_score=row.risk_score,
        customer_response_allowed=row.customer_response_allowed,
        requires_human_review=row.requires_human_review,
        audit_reference=row.audit_reference,
        audit_events=list(_to_persisted_events(row.audit_events)),
    )


def _to_persisted_events(rows: Iterable[AuditEventRow]) -> Iterable[PersistedAuditEvent]:
    for row in rows:
        yield PersistedAuditEvent(
            sequence_number=row.sequence_number,
            name=row.name,
            created_at=_as_utc(row.created_at),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
