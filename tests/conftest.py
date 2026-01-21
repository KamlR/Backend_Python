import pytest
from fastapi.testclient import TestClient
from main import app
from typing import Generator


@pytest.fixture
def app_client() -> Generator[TestClient, None, None]:
    return TestClient(app)
