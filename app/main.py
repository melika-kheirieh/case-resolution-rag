import logging
from uuid import uuid4

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import HTMLResponse

from app.services.demo_seed import build_demo_store
from app.services.evaluation import run_demo_evaluation
from app.services.investigation import InvestigationService
from app.services.audit_repository_factory import build_investigation_audit_repository
from app.services.logging_config import configure_logging, correlation_id_var, request_id_var
from app.services.policy_retrieval_factory import build_policy_retrieval_service
from app.services.provider import FakeProvider

configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title="Operations Case Resolution Backend", version="0.3.0")
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


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or f"req_{uuid4().hex[:12]}"
    correlation_id = request.headers.get("x-correlation-id") or request_id
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id

    request_token = request_id_var.set(request_id)
    correlation_token = correlation_id_var.set(correlation_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )
        return response
    except Exception:
        logger.exception(
            "request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
            },
        )
        raise
    finally:
        request_id_var.reset(request_token)
        correlation_id_var.reset(correlation_token)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo", response_class=HTMLResponse)
def demo_page() -> str:
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <title>Operations Case Resolution Demo</title>
        <style>
          body { font-family: system-ui, sans-serif; max-width: 920px; margin: 40px auto; }
          button { padding: 10px 14px; cursor: pointer; margin-right: 8px; }
          pre { background: #111827; color: #f9fafb; padding: 16px; overflow: auto; }
        </style>
      </head>
      <body>
        <h1>Operations Case Resolution Demo</h1>
        <p>Run one of the synthetic refund-delay cases.</p>
        <button data-case-id="case_refund_delay_002">Auto-resolution candidate</button>
        <button data-case-id="case_refund_delay_001">SLA breach</button>
        <button data-case-id="case_refund_delay_missing_evidence">Missing evidence</button>
        <button data-case-id="case_refund_delay_expired_policy">Expired policy</button>
        <button data-case-id="case_refund_delay_policy_conflict">Policy conflict</button>
        <button data-case-id="case_refund_delay_refund_failed">Refund failed</button>
        <button data-case-id="case_refund_delay_within_sla">Within SLA</button>
        <button data-case-id="case_refund_delay_policy_version_mismatch">Version mismatch</button>
        <button id="failure-gallery">Failure gallery</button>
        <button id="eval">Run eval report</button>
        <pre id="output">Click the button to generate a ResolutionPacket.</pre>
        <script>
          document.querySelectorAll("button[data-case-id]").forEach((button) => {
            button.onclick = async () => {
              const caseId = button.dataset.caseId;
              const response = await fetch(`/cases/${caseId}/investigate`, { method: "POST" });
              const data = await response.json();
              document.getElementById("output").textContent = JSON.stringify(data, null, 2);
            };
          });
          document.getElementById("failure-gallery").onclick = async () => {
            const response = await fetch("/demo/failure-gallery");
            const data = await response.json();
            document.getElementById("output").textContent = JSON.stringify(data, null, 2);
          };
          document.getElementById("eval").onclick = async () => {
            const response = await fetch("/eval/demo");
            const data = await response.json();
            document.getElementById("output").textContent = JSON.stringify(data, null, 2);
          };
        </script>
      </body>
    </html>
    """


@app.get("/demo/cases/{case_id}")
def get_demo_case(case_id: str):
    return store.get_case(case_id)


@app.get("/demo/failure-gallery")
def failure_gallery():
    gallery = [
        _failure_gallery_item(case_id=case_id, service=investigation_service)
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


@app.get("/investigation-runs/{run_id}")
def get_investigation_run(run_id: str):
    run = audit_repository.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Investigation run not found.")
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
