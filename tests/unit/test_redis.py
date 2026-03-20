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

async def test_post_predict_has_cache(async_client, app, allow_model):
    """
    Проверяем логику работы ручки /predict, если данные в кэше есть
    """
    app.state.model = allow_model 

    redis_client = AsyncMock()
    cached_payload = {"is_violation": False, "proba": 0.12}
    redis_client.get.return_value = json.dumps(cached_payload)
    redis_client.set = AsyncMock()
    app.state.redis_client = redis_client

    resp = await async_client.post("/predict", json=PREDICT_BASE_PAYLOAD)

    # assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_violation"] is False
    assert body["probability"] == 0.12

    # redis calls
    redis_client.get.assert_awaited_once_with("prediction:1")
    redis_client.set.assert_not_awaited()

async def test_post_predict_no_cache(async_client, app, allow_model):
    """
    Проверяем логику работы ручки /predict, если данных в кэше нет.
    """
    # arrange
    app.state.model = allow_model  # probability=0.8 => is_violation=True

    redis_client = AsyncMock()
    redis_client.get.return_value = None
    redis_client.set = AsyncMock()
    app.state.redis_client = redis_client

    # act
    resp = await async_client.post("/predict", json=PREDICT_BASE_PAYLOAD)

    # assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_violation"] is True
    assert body["probability"] == 0.8

    # cache read
    redis_client.get.assert_awaited_once_with("prediction:1")

    # cache write: проверяем key/ex и содержимое JSON
    redis_client.set.assert_awaited_once()
    args, kwargs = redis_client.set.await_args

    # args: (key, value_json)
    assert args[0] == "prediction:1"
    saved = json.loads(args[1])
    assert saved["is_violation"] is True
    assert saved["proba"] == 0.8

    # kwargs: ex=15
    assert kwargs.get("ex") == 15


async def test_post_async_predict_set_cache(async_client, app):
    """
    Проверяем логику работы ручки /async-predict, тут должен вызываться только set для кэша.
    """
    # мок Redis client
    redis_client = AsyncMock()
    redis_client.get = AsyncMock()
    redis_client.set = AsyncMock()
    app.state.redis_client = redis_client

    # мок для Kafka
    kafka = AsyncMock()
    kafka.send_moderation_request = AsyncMock()
    app.state.kafka = kafka

    # то, что вернёт репозиторий создания задачи
    created_task = {
        "task_id": 123,
        "status": "pending",
        "is_violation": None,
        "probability": None,
        "error_message": None,
    }

    # мокаем поход в репозиторий (работа с бд)
    with patch("services.async_moderation.ItemRepository") as ItemRepoMock, \
         patch("services.async_moderation.ModerationResultRepository") as ModerRepoMock:

        item_repo_instance = ItemRepoMock.return_value
        item_repo_instance.check_adv_existance = AsyncMock(return_value=True)

        moder_repo_instance = ModerRepoMock.return_value
        moder_repo_instance.create_moderation_result = AsyncMock(return_value=created_task)
        response = await async_client.post("/async-predict", json={"item_id": 5})

    # выполняем запрос
    assert response.status_code == 200
    body = response .json()
    assert body["task_id"] == 123
    assert body["status"] == "pending"

     # redis get не трогали 
    redis_client.get.assert_not_awaited()

    # redis set вызван корректно
    redis_client.set.assert_awaited_once()
    args, kwargs = redis_client.set.await_args

    # args: (key, value_json)
    assert args[0] == "async_prediction:123"
    saved_payload = json.loads(args[1])

    assert saved_payload["task_id"] == 123
    assert saved_payload["status"] == "pending"
    assert saved_payload["is_violation"] is None
    assert saved_payload["probability"] is None
    assert saved_payload["error_message"] is None

    # kwargs: ex=5
    assert kwargs.get("ex") == 5


async def test_get_moderation_result_no_cache(async_client, app):
    """
    Проверяем логику работы ручки /moderation-result/{task_id}, когда данных в кэше нет.
    """
    # мок для redis
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    redis_client.set = AsyncMock()
    app.state.redis_client = redis_client

    current_task_status = {
        "task_id": 123,
        "status": "pending",
        "is_violation": None,
        "probability": None,
        "error_message": None,
    }
     # мокаем поход в репозиторий (работа с бд)
    with patch("services.async_moderation.ModerationResultRepository") as ModerRepoMock:
        moder_repo_instance = ModerRepoMock.return_value
        moder_repo_instance.get_moderation_result = AsyncMock(return_value=current_task_status)
        response = await async_client.get("/moderation-result/123")
    
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == 123
    assert body["status"] == "pending"
    assert body["is_violation"] is None
    assert body["probability"] is None
    assert body["message"] is None

    # cache read
    redis_client.get.assert_awaited_once_with("async_prediction:123")

    # cache write: проверяем key/ex и содержимое JSON
    redis_client.set.assert_awaited_once()
    args, kwargs = redis_client.set.await_args
    # args: (key, value_json)
    assert args[0] == "async_prediction:123"

    saved_payload = json.loads(args[1])
    assert saved_payload["task_id"] == 123
    assert saved_payload["status"] == "pending"
    assert saved_payload["is_violation"] is None
    assert saved_payload["probability"] is None
    assert saved_payload["error_message"] is None

    # kwargs: ex=5
    assert kwargs.get("ex") == 15



async def test_get_moderation_result_has_cache(async_client, app):
    """
    Проверяем логику работы ручки /moderation-result/{task_id}, когда данные есть в кэше.
    """
    # мок для redis
    redis_client = AsyncMock()
    cached_payload = {"task_id": 123, "status": "ready", "is_violation": True, "probability": 0.8,
        "error_message": None,}
    redis_client.get.return_value = json.dumps(cached_payload)
    redis_client.set = AsyncMock()
    app.state.redis_client = redis_client

    response = await async_client.get("/moderation-result/123")
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == 123
    assert body["status"] == "ready"
    assert body["is_violation"] is True
    assert body["probability"] == 0.8
    assert body["message"] is None

    # redis calls
    redis_client.get.assert_awaited_once_with("async_prediction:123")
    redis_client.set.assert_not_awaited()