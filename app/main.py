from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.demo_page import DEMO_PAGE_HTML
from app.middleware.request_context import request_context_middleware
from app.services.audit_repository_factory import (
    build_investigation_audit_repository,
)
from app.services.demo_seed import build_demo_store
from app.services.evaluation import run_demo_evaluation
from app.services.investigation import InvestigationService
from app.services.logging_config import configure_logging
from app.services.policy_retrieval_factory import (
    build_policy_retrieval_service,
)
from app.services.provider import FakeProvider


configure_logging()

app = FastAPI(
    title="Operations Case Resolution Backend",
    version="0.3.0",
)

app.middleware("http")(request_context_middleware)

store = build_demo_store()
policy_retrieval = build_policy_retrieval_service(store.list_policies())
audit_repository = build_investigation_audit_repository()

investigation_service = InvestigationService(
    store=store,
    policy_retrieval=policy_retrieval,
    audit_repository=audit_repository,
)

bad_provider_service = InvestigationService(
    store=store,
    policy_retrieval=policy_retrieval,
    provider=FakeProvider(mode="bad_output"),
    audit_repository=audit_repository,
)

FAILURE_GALLERY_CASE_IDS = [
    "case_refund_delay_001",
    "case_refund_delay_missing_evidence",
    "case_refund_delay_expired_policy",
    "case_refund_delay_policy_conflict",
    "case_refund_delay_refund_failed",
    "case_refund_delay_within_sla",
    "case_refund_delay_policy_version_mismatch",
]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo", response_class=HTMLResponse)
def demo_page() -> str:
    return DEMO_PAGE_HTML


@app.get("/demo/cases/{case_id}")
def get_demo_case(case_id: str):
    return store.get_case(case_id)


@app.get("/demo/failure-gallery")
def failure_gallery():
    gallery = [
        _failure_gallery_item(
            case_id=case_id,
            service=investigation_service,
        )
        for case_id in FAILURE_GALLERY_CASE_IDS
    ]

    gallery.append(
        _failure_gallery_item(
            case_id="case_refund_delay_002",
            service=bad_provider_service,
            scenario_id="bad_ai_response",
        )
    )

    return {"scenarios": gallery}


@app.post("/demo/cases/{case_id}/investigations")
def run_investigation(case_id: str):
    return investigation_service.run(case_id)


@app.post("/cases/{case_id}/investigate")
def investigate_case(case_id: str):
    return investigation_service.run(case_id)


@app.get("/investigation-runs")
def list_investigation_runs(
    limit: int = Query(default=20, ge=1, le=100),
):
    return {
        "limit": limit,
        "runs": audit_repository.list_recent(limit=limit),
    }


@app.get("/investigation-runs/{run_id}")
def get_investigation_run(run_id: str):
    run = audit_repository.get(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation run not found.",
        )

    return run


@app.get("/eval/demo")
def evaluate_demo_cases():
    return run_demo_evaluation(investigation_service)


def _failure_gallery_item(
    *,
    case_id: str,
    service: InvestigationService,
    scenario_id: str | None = None,
) -> dict[str, object]:
    packet = service.run(case_id)

    return {
        "scenario_id": scenario_id or case_id,
        "case_id": case_id,
        "recommended_action": packet.recommended_action,
        "automation_decision": packet.automation_decision,
        "automation_blockers": packet.automation_blockers,
        "readiness": packet.readiness.status,
        "risk_gate": packet.risk_gate,
        "customer_response_allowed": packet.customer_response_allowed,
        "requires_human_review": packet.requires_human_review,
        "investigation_run_id": packet.investigation_run_id,
        "audit_reference": packet.audit_reference,
    }