import pytest
import json
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


@pytest.mark.integration
async def test_post_predict_has_cache_integration(async_client, app, allow_model, redis_client):
    """
    /predict: данные уже есть в redis -> ответ берётся из кэша,
    в redis ничего не перезаписываем.
    """
    app.state.model = allow_model
    app.state.redis_client = redis_client

    # предварительно кладём кэш (как делает RedisPredictionStorage.set)
    await redis_client.set("prediction:1", json.dumps({"is_violation": False, "proba": 0.12}), ex=15)

    resp = await async_client.post("/predict", json=PREDICT_BASE_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_violation"] is False
    assert body["probability"] == 0.12

    # проверяем, что значение в redis осталось корректным
    raw = await redis_client.get("prediction:1")
    assert json.loads(raw) == {"is_violation": False, "proba": 0.12}


@pytest.mark.integration
async def test_post_predict_no_cache_integration(async_client, app, allow_model, redis_client):
    """
    /predict: кэша нет -> сервис считает моделью -> кладёт результат в redis.
    """
    app.state.model = allow_model
    app.state.redis_client = redis_client

    # убеждаемся, что ключа нет
    assert await redis_client.get("prediction:1") is None

    resp = await async_client.post("/predict", json=PREDICT_BASE_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_violation"] is True
    assert body["probability"] == 0.8

    # проверяем, что сервис действительно записал кэш
    raw = await redis_client.get("prediction:1")
    assert raw is not None
    saved = json.loads(raw)
    assert saved["is_violation"] is True
    assert saved["proba"] == 0.8

    # TTL должен быть установлен
    ttl = await redis_client.ttl("prediction:1")
    assert ttl == 15


@pytest.mark.integration
async def test_post_async_predict_set_cache_integration(async_client, app, redis_client):
    """
    /async-predict: prepare_data_for_moderation кладёт created_task в redis по key async_prediction:{task_id}.
    Репозитории и kafka мокнуты, redis настоящий (fakeredis).
    """
    app.state.redis_client = redis_client

    kafka = AsyncMock()
    kafka.send_moderation_request = AsyncMock()
    app.state.kafka = kafka

    created_task = {
        "task_id": 123,
        "status": "pending",
        "is_violation": None,
        "probability": None,
        "error_message": None,
    }

    with patch("services.async_moderation.ItemRepository") as ItemRepoMock, \
         patch("services.async_moderation.ModerationResultRepository") as ModerRepoMock:

        ItemRepoMock.return_value.check_adv_existance = AsyncMock(return_value=True)
        ModerRepoMock.return_value.create_moderation_result = AsyncMock(return_value=created_task)

        response = await async_client.post("/async-predict", json={"item_id": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == 123
    assert body["status"] == "pending"

    # проверяем, что в redis появился ключ и данные там корректные
    raw = await redis_client.get("async_prediction:123")
    assert raw is not None
    saved = json.loads(raw)
    assert saved == created_task

    ttl = await redis_client.ttl("async_prediction:123")
    assert ttl == 5


@pytest.mark.integration
async def test_get_moderation_result_no_cache_integration(async_client, app, redis_client):
    """
    /moderation-result/{task_id}: если в redis нет -> берём из repo -> кладём в redis.
    """
    app.state.redis_client = redis_client

    current_task_status = {
        "task_id": 123,
        "status": "pending",
        "is_violation": None,
        "probability": None,
        "error_message": None,
    }

    # ключа нет
    assert await redis_client.get("async_prediction:123") is None

    with patch("services.async_moderation.ModerationResultRepository") as ModerRepoMock:
        ModerRepoMock.return_value.get_moderation_result = AsyncMock(return_value=current_task_status)
        response = await async_client.get("/moderation-result/123")

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == 123
    assert body["status"] == "pending"
    assert body["is_violation"] is None
    assert body["probability"] is None
    assert body["message"] is None

    # после запроса кэш должен появиться
    raw = await redis_client.get("async_prediction:123")
    assert raw is not None
    saved = json.loads(raw)
    assert saved == current_task_status

    ttl = await redis_client.ttl("async_prediction:123")
    assert ttl == 15


@pytest.mark.integration
async def test_get_moderation_result_has_cache_integration(async_client, app, redis_client):
    """
    /moderation-result/{task_id}: если в redis есть -> repo не трогаем, отдаём из кэша.
    """
    app.state.redis_client = redis_client

    cached_payload = {
        "task_id": 123,
        "status": "ready",
        "is_violation": True,
        "probability": 0.8,
        "error_message": None,
    }

    await redis_client.set("async_prediction:123", json.dumps(cached_payload), ex=15)

    with patch("services.async_moderation.ModerationResultRepository") as ModerRepoMock:
        ModerRepoMock.return_value.get_moderation_result = AsyncMock()
        response = await async_client.get("/moderation-result/123")

        # repo не должен вызываться
        ModerRepoMock.return_value.get_moderation_result.assert_not_awaited()

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == 123
    assert body["status"] == "ready"
    assert body["is_violation"] is True
    assert body["probability"] == 0.8
    assert body["message"] is None

