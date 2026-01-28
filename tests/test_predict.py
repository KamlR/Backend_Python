from http import HTTPStatus
import pytest
from unittest.mock import AsyncMock
from services import moderation

BASE_PAYLOAD = {
    "seller_id": 1,
    "item_id": 1,
    "name": "Item",
    "description": "Nice item",
    "category": 10,
    "is_verified_seller": False,
    "images_qty": 2,
}


def test_predict_violation_true(app_client, allow_model):
    app_client.app.state.model = allow_model

    response = app_client.post("/predict", json=BASE_PAYLOAD)

    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["is_violation"] is True
    assert 0 <= data["probability"] <= 1

def test_predict_violation_false(app_client, deny_model):
    app_client.app.state.model = deny_model

    response = app_client.post("/predict", json=BASE_PAYLOAD)

    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["is_violation"] is False
    assert 0 <= data["probability"] <= 1

def test_predict_validation_wrong_type(app_client):
    response = app_client.post(
        "/predict",
        json={
            "seller_id": "not_a_number",
            "is_verified_seller": True,
            "item_id": 2,
            "name": "Phone",
            "description": "Good phone",
            "category": 1,
            "images_qty": 1,
        },
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

def test_predict_model_not_loaded(app_client):
    app_client.app.state.model = None

    response = app_client.post("/predict", json=BASE_PAYLOAD)

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Model not loaded"
