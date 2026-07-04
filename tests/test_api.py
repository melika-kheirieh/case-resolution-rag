def test_health_returns_ok(test_client):
    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
    assert data["customer_response_allowed"] is False
    assert data["requires_human_review"] is True


def test_demo_eval_returns_all_golden_cases_passing(test_client):
    response = test_client.get("/eval/demo")

    assert response.status_code == 200
    data = response.json()
    assert data["total_cases"] == 5
    assert data["passed_cases"] == 5
