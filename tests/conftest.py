import pytest
from fastapi.testclient import TestClient
from main import app


class FakeModel:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, X):
        return [[1 - self.probability, self.probability]]


@pytest.fixture
def app_client():
    return TestClient(app)


@pytest.fixture
def allow_model():
    return FakeModel(probability=0.8)  # нарушение = True


@pytest.fixture
def deny_model():
    return FakeModel(probability=0.1)  # нарушение = False
