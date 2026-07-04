import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.demo_seed import build_demo_store
from app.services.investigation import InvestigationService


@pytest.fixture
def demo_store():
    return build_demo_store()


@pytest.fixture
def investigation_service(demo_store):
    return InvestigationService(store=demo_store)


@pytest.fixture
def test_client():
    return TestClient(app)
