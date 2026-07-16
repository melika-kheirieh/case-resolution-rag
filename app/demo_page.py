DEMO_PAGE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Operations Case Resolution Demo</title>
    <style>
      body {
        font-family: system-ui, sans-serif;
        max-width: 920px;
        margin: 40px auto;
      }

      button {
        padding: 10px 14px;
        cursor: pointer;
        margin-right: 8px;
      }

      pre {
        background: #111827;
        color: #f9fafb;
        padding: 16px;
        overflow: auto;
      }
    </style>
  </head>

  <body>
    <h1>Operations Case Resolution Demo</h1>
    <p>Run one of the synthetic refund-delay cases.</p>

    <button data-case-id="case_refund_delay_002">
      Auto-resolution candidate
    </button>

    <button data-case-id="case_refund_delay_001">
      SLA breach
    </button>

    <button data-case-id="case_refund_delay_missing_evidence">
      Missing evidence
    </button>

    <button data-case-id="case_refund_delay_expired_policy">
      Expired policy
    </button>

    <button data-case-id="case_refund_delay_policy_conflict">
      Policy conflict
    </button>

    <button data-case-id="case_refund_delay_refund_failed">
      Refund failed
    </button>

    <button data-case-id="case_refund_delay_within_sla">
      Within SLA
    </button>

    <button data-case-id="case_refund_delay_policy_version_mismatch">
      Version mismatch
    </button>

    <button id="failure-gallery">
      Failure gallery
    </button>

    <button id="eval">
      Run eval report
    </button>

    <pre id="output">
Click the button to generate a ResolutionPacket.
    </pre>

    <script>
      document
        .querySelectorAll("button[data-case-id]")
        .forEach((button) => {
          button.onclick = async () => {
            const caseId = button.dataset.caseId;
            const response = await fetch(
              `/cases/${caseId}/investigate`,
              { method: "POST" }
            );

            const data = await response.json();

            document.getElementById("output").textContent =
              JSON.stringify(data, null, 2);
          };
        });

      document.getElementById("failure-gallery").onclick = async () => {
        const response = await fetch("/demo/failure-gallery");
        const data = await response.json();

        document.getElementById("output").textContent =
          JSON.stringify(data, null, 2);
      };

      document.getElementById("eval").onclick = async () => {
        const response = await fetch("/eval/demo");
        const data = await response.json();

        document.getElementById("output").textContent =
          JSON.stringify(data, null, 2);
      };
    </script>
  </body>
</html>
"""