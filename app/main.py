from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.services.demo_seed import build_demo_store
from app.services.evaluation import run_demo_evaluation
from app.services.investigation import InvestigationService

app = FastAPI(title="Operations Case Resolution Backend", version="0.2.0")
store = build_demo_store()
investigation_service = InvestigationService(store=store)


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


@app.post("/demo/cases/{case_id}/investigations")
def run_investigation(case_id: str):
    return investigation_service.run(case_id)


@app.post("/cases/{case_id}/investigate")
def investigate_case(case_id: str):
    return investigation_service.run(case_id)


@app.get("/eval/demo")
def evaluate_demo_cases():
    return run_demo_evaluation(investigation_service)
