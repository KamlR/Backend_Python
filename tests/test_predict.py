from http import HTTPStatus
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

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


@pytest.mark.asyncio
async def test_close_item_ok_without_async_task(async_client, allow_model):
    """
    item удалён, в ModerationResultRepository.delete_task вернул None,
    значит удаляем только prediction:item_id и НЕ трогаем async_prediction.
    """
    async_client._transport.app.state.model = allow_model

    # redis client (внутри RedisPredictionStorage)
    redis_mock = MagicMock()
    async_client._transport.app.state.redis_client = redis_mock

    # Мокаем ItemRepository и ModerationResultRepository в модуле services.moderation
    with patch("services.moderation.ItemRepository") as ItemRepoMock, \
         patch("services.moderation.ModerationResultRepository") as ModerRepoMock, \
         patch("services.moderation.RedisPredictionStorage") as StorageMock:

        # itemRepository.delete_item -> True
        ItemRepoMock.return_value.delete_item = AsyncMock(return_value=True)

        # moderation repo delete_task -> None (нет async-задачи)
        ModerRepoMock.return_value.delete_task = AsyncMock(return_value=None)

        # storage: delete await-ится, change_key_prefix обычный
        storage_instance = StorageMock.return_value
        storage_instance.delete = AsyncMock(return_value=None)
        storage_instance.change_key_prefix = MagicMock()

        resp = await async_client.delete("/close/10")

    assert resp.status_code == HTTPStatus.OK

    ItemRepoMock.return_value.delete_item.assert_awaited_once_with(10)
    storage_instance.delete.assert_awaited_once_with(10)

    ModerRepoMock.return_value.delete_task.assert_awaited_once_with(10)
    storage_instance.change_key_prefix.assert_not_called()


@pytest.mark.asyncio
async def test_close_item_ok_with_async_task_deleted(async_client, allow_model):
    """
    item удалён, delete_task вернул task_id -> должны:
    1) удалить prediction:item_id
    2) переключить префикс на async_prediction
    3) удалить async task по task_id
    """
    async_client._transport.app.state.model = allow_model

    redis_mock = MagicMock()
    async_client._transport.app.state.redis_client = redis_mock

    with patch("services.moderation.ItemRepository") as ItemRepoMock, \
         patch("services.moderation.ModerationResultRepository") as ModerRepoMock, \
         patch("services.moderation.RedisPredictionStorage") as StorageMock:

        ItemRepoMock.return_value.delete_item = AsyncMock(return_value=True)
        ModerRepoMock.return_value.delete_task = AsyncMock(return_value=777)

        storage_instance = StorageMock.return_value
        storage_instance.delete = AsyncMock(return_value=None)
        storage_instance.change_key_prefix = MagicMock()

        resp = await async_client.delete("/close/10")

    assert resp.status_code == HTTPStatus.OK

    ItemRepoMock.return_value.delete_item.assert_awaited_once_with(10)
    ModerRepoMock.return_value.delete_task.assert_awaited_once_with(10)

    # delete должен быть вызван дважды: сначала item_id, потом task_id
    assert storage_instance.delete.await_count == 2
    storage_instance.delete.assert_any_await(10)
    storage_instance.change_key_prefix.assert_called_once_with("async_prediction")
    storage_instance.delete.assert_any_await(777)


@pytest.mark.asyncio
async def test_close_item_not_found(async_client, allow_model):
    """
    ItemRepository.delete_item -> False => ItemNotFoundError => 404
    """
    async_client._transport.app.state.model = allow_model

    redis_mock = MagicMock()
    async_client._transport.app.state.redis_client = redis_mock

    with patch("services.moderation.ItemRepository") as ItemRepoMock, \
         patch("services.moderation.RedisPredictionStorage") as StorageMock:

        ItemRepoMock.return_value.delete_item = AsyncMock(return_value=False)

        storage_instance = StorageMock.return_value
        storage_instance.delete = AsyncMock(return_value=None)

        resp = await async_client.delete("/close/999")

    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.json()["detail"] == "Item not found"

    ItemRepoMock.return_value.delete_item.assert_awaited_once_with(999)
    storage_instance.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_close_item_internal_error(async_client, allow_model):
    """
    Любая другая ошибка => 500 Close item failed
    Например, delete_item кидает исключение.
    """
    async_client._transport.app.state.model = allow_model

    redis_mock = MagicMock()
    async_client._transport.app.state.redis_client = redis_mock

    with patch("services.moderation.ItemRepository") as ItemRepoMock:
        ItemRepoMock.return_value.delete_item = AsyncMock(side_effect=RuntimeError("db down"))

        resp = await async_client.delete("/close/10")

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert resp.json()["detail"] == "Close item failed"