from http import HTTPStatus
import pytest
from unittest.mock import AsyncMock, patch

PREDICT_BASE_PAYLOAD = {
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

    response = app_client.post("/predict", json=PREDICT_BASE_PAYLOAD)

    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["is_violation"] is True
    assert 0 <= data["probability"] <= 1

def test_predict_violation_false(app_client, deny_model):
    app_client.app.state.model = deny_model

    response = app_client.post("/predict", json=PREDICT_BASE_PAYLOAD)

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

    response = app_client.post("/predict", json=PREDICT_BASE_PAYLOAD)

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Model not loaded"


async def test_simple_predict_violation_true(app_client, allow_model):
    app_client.app.state.model = allow_model

    with patch("services.moderation.ItemRepository") as ItemRepoMock:
        item_repo_instance = ItemRepoMock.return_value
        item_repo_instance.get_item_for_prediction = AsyncMock(return_value=PREDICT_BASE_PAYLOAD)
        response = app_client.post("/simple-predict", json={"item_id": 1})

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["is_violation"] is True
    assert 0 <= data["probability"] <= 1



async def test_simple_predict_violation_false(app_client, deny_model):
    app_client.app.state.model = deny_model
    
    with patch("services.moderation.ItemRepository") as ItemRepoMock:
        item_repo_instance = ItemRepoMock.return_value
        item_repo_instance.get_item_for_prediction = AsyncMock(return_value=PREDICT_BASE_PAYLOAD)
        response = app_client.post("/simple-predict", json={"item_id": 1})

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["is_violation"] is False
    assert 0 <= data["probability"] <= 1


async def test_simple_predict_item_not_found(app_client, deny_model):
    app_client.app.state.model = deny_model

    with patch("services.moderation.ItemRepository") as ItemRepoMock:
        item_repo_instance = ItemRepoMock.return_value
        item_repo_instance.get_item_for_prediction = AsyncMock(return_value=None)
        response = app_client.post("/simple-predict", json={"item_id": 1})

    assert response.status_code == HTTPStatus.NOT_FOUND
    data = response.json()
    assert data["detail"] == "Item not found"


