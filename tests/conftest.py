import pytest
from starlette.testclient import TestClient

from app.services.audit_repository import InvestigationAuditRepository
from app.services.demo_seed import build_demo_store
from app.services.investigation import InvestigationService
from app.services.policy_retrieval_factory import build_policy_retrieval_service
from app.services.provider import FakeProvider


@pytest.fixture
def demo_store():
    return build_demo_store()


@pytest.fixture
def investigation_service(demo_store):
    return InvestigationService(store=demo_store)


@pytest.fixture
def test_client(tmp_path, monkeypatch):
    audit_db_url = f"sqlite:///{tmp_path / 'audit.db'}"
    monkeypatch.setenv("AUDIT_DATABASE_URL", audit_db_url)

    from app import main as app_main

    store = build_demo_store()
    policy_retrieval = build_policy_retrieval_service(store.list_policies())
    audit_repository = InvestigationAuditRepository(audit_db_url)
    audit_repository.ensure_schema()

    monkeypatch.setattr(app_main, "store", store)
    monkeypatch.setattr(app_main, "policy_retrieval", policy_retrieval)
    monkeypatch.setattr(app_main, "audit_repository", audit_repository)
    monkeypatch.setattr(
        app_main,
        "investigation_service",
        InvestigationService(
            store=store,
            policy_retrieval=policy_retrieval,
            audit_repository=audit_repository,
        ),
    )
    monkeypatch.setattr(
        app_main,
        "bad_provider_service",
        InvestigationService(
            store=store,
            policy_retrieval=policy_retrieval,
            provider=FakeProvider(mode="bad_output"),
            audit_repository=audit_repository,
        ),
    )

    return TestClient(app_main.app)
