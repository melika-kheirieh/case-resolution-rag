def test_health_returns_ok(test_client):
    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"].startswith("req_")
    assert response.headers["X-Correlation-ID"] == response.headers["X-Request-ID"]


def test_request_context_is_returned_and_recorded_in_packet(test_client):
    response = test_client.post(
        "/cases/case_refund_delay_002/investigate",
        headers={
            "X-Request-ID": "req_interview_demo",
            "X-Correlation-ID": "corr_case_resolution_demo",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req_interview_demo"
    assert response.headers["X-Correlation-ID"] == "corr_case_resolution_demo"
    data = response.json()
    assert data["request_id"] == "req_interview_demo"
    assert data["correlation_id"] == "corr_case_resolution_demo"


def test_investigate_completed_refund_returns_auto_resolve_candidate(test_client):
    response = test_client.post("/cases/case_refund_delay_002/investigate")

    assert response.status_code == 200
    data = response.json()
    assert data["recommended_action"] == "resolve"
    assert data["automation_decision"] == "auto_resolve_candidate"
    assert data["automation_blockers"] == []
    assert data["citations"]
    assert data["retrieval_run"]["status"] == "policy_retrieved"
    assert data["readiness"]["status"] == "ready"
    assert data["risk_gate"]["passed"] is True
    assert data["risk_gate"]["risk_level"] == "low"
    assert data["customer_response_allowed"] is True
    assert data["requires_human_review"] is False


def test_investigate_policy_conflict_returns_manual_review_required(test_client):
    response = test_client.post("/cases/case_refund_delay_policy_conflict/investigate")

    assert response.status_code == 200
    data = response.json()
    assert data["recommended_action"] == "request_more_info"
    assert data["automation_decision"] == "manual_review_required"
    assert data["automation_blockers"] == ["policy_conflict"]
    assert len(data["citations"]) == 2
    assert data["retrieval_run"]["status"] == "policy_conflict"
    assert data["readiness"]["status"] == "policy_conflict"
    assert data["risk_gate"]["passed"] is False
    assert data["customer_response_allowed"] is False
    assert data["requires_human_review"] is True


def test_failure_gallery_lists_failure_scenarios(test_client):
    response = test_client.get("/demo/failure-gallery")

    assert response.status_code == 200
    data = response.json()
    scenario_ids = {scenario["scenario_id"] for scenario in data["scenarios"]}

    assert {
        "case_refund_delay_001",
        "case_refund_delay_missing_evidence",
        "case_refund_delay_expired_policy",
        "case_refund_delay_policy_conflict",
        "case_refund_delay_refund_failed",
        "case_refund_delay_within_sla",
        "case_refund_delay_policy_version_mismatch",
        "bad_ai_response",
    }.issubset(scenario_ids)
    failed_refund = next(
        scenario
        for scenario in data["scenarios"]
        if scenario["scenario_id"] == "case_refund_delay_refund_failed"
    )
    assert failed_refund["automation_decision"] == "manual_review_required"
    assert failed_refund["risk_gate"]["risk_level"] == "high"
    assert "refund_failed_operator_review_required" in failed_refund["automation_blockers"]


def test_demo_eval_returns_all_golden_cases_passing(test_client):
    response = test_client.get("/eval/demo")

    assert response.status_code == 200
    data = response.json()
    assert data["total_cases"] == 9
    assert data["passed_cases"] == 9
    assert data["decision_accuracy"] == 1.0
    assert data["retrieval_hit_rate"] == 1.0
    assert data["manual_review_accuracy"] == 1.0
    assert data["unsafe_response_block_rate"] == 1.0
