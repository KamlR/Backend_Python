from http import HTTPStatus
import pytest
from unittest.mock import AsyncMock
from services import moderation

@pytest.mark.parametrize("payload, expected", [
    ({"is_verified_seller": True, "images_qty": 0}, True),
    ({"is_verified_seller": True, "images_qty": 1}, True),
    ({"is_verified_seller": True}, True),
])
def test_predict_verified_seller_allowed(app_client, payload, expected):
    base = {
        "seller_id": 1,
        "item_id": 1,
        "name": "Item",
        "description": "Desc",
        "category": 1,
    }
    base.update(payload)

    response = app_client.post("/predict", json=base)
    assert response.status_code == HTTPStatus.OK
    assert response.json()["is_allowed"] is expected
     

@pytest.mark.parametrize("payload, expected", [
    ({"is_verified_seller": False, "images_qty": 1}, True),
    ({"is_verified_seller": False, "images_qty": 5}, True)
])
def test_predict_seller_with_images_allowed(app_client, payload, expected):
    base = {
        "seller_id": 1,
        "item_id": 1,
        "name": "Item",
        "description": "Desc",
        "category": 1,
    }
    base.update(payload)

    response = app_client.post("/predict", json=base)
    assert response.status_code == HTTPStatus.OK
    assert response.json()["is_allowed"] is expected


@pytest.mark.parametrize("payload, expected", [
    ({"is_verified_seller": False, "images_qty": 0}, False),
    ({"is_verified_seller": False}, False)
])
def test_predict_seller_not_allowed(app_client, payload, expected):
    base = {
        "seller_id": 1,
        "item_id": 1,
        "name": "Item",
        "description": "Desc",
        "category": 1,
    }
    base.update(payload)

    response = app_client.post("/predict", json=base)
    assert response.status_code == HTTPStatus.OK
    assert response.json()["is_allowed"] is expected


def test_predict_validation_wrong_type(app_client):
    response = app_client.post(
        "/predict",
        json={
            "seller_id": "not_a_number",
            "is_verified_seller": True,
            "item_id": 2,
            "name": "Phone",
            "description": "Good phone",
            "category": 1
        }
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_predict_validation_missing_field(app_client):
  response = app_client.post(
      "/predict",
      json={
          "seller_id": 1,
          "is_verified_seller": True,
          "item_id": 2,
          "description": "No name"
      }
  )

  assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_predict_business_logic_error(app_client, monkeypatch):
    async def mock_predict(dto):
        raise Exception("Service failed")

    monkeypatch.setattr(
        moderation.ModerationService,
        "predict",
        AsyncMock(side_effect=mock_predict)
    )

    response = app_client.post(
        "/predict",
        json={
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 2,
            "name": "Phone",
            "description": "Good phone",
            "category": 1
        }
    )

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "Prediction failed"