import pytest
from unittest.mock import AsyncMock, call, patch

from db.connection import PostgresConnection
from app.workers.moderation_worker import ModerationConsumer
from app.workers.retry_moderation_worker import RetryModerationConsumer
import json

class FakeMsg:
    def __init__(self, value: bytes):
        self.value = value


class FakeConsumer:
    """
    Фейковый AIOKafkaConsumer:
    - async-итератор, отдающий список сообщений
    - commit() / stop() — async методы
    """
    def __init__(self, messages):
        self._messages = messages
        self.commit = AsyncMock()
        self.stop = AsyncMock()

    def __aiter__(self):
        async def gen():
            for m in self._messages:
                yield m
        return gen()


def test_async_predict_creates_task_and_sends_to_kafka(app_client):
    kafka_mock = AsyncMock()
    kafka_mock.send_moderation_request = AsyncMock()
    app_client.app.state.kafka = kafka_mock

    redis_client = AsyncMock()
    redis_client.get = AsyncMock()
    redis_client.set = AsyncMock()
    app_client.app.state.redis_client = redis_client

    created_task = {
        "task_id": 123,
        "status": "pending",
        "is_violation": None,
        "probability": None,
        "error_message": None,
    }

    with patch("services.async_moderation.ItemRepository") as ItemRepoMock, \
         patch("services.async_moderation.ModerationResultRepository") as ModerRepoMock:

        item_repo_instance = ItemRepoMock.return_value
        item_repo_instance.check_adv_existance = AsyncMock(return_value=True)

        moder_repo_instance = ModerRepoMock.return_value
        moder_repo_instance.create_moderation_result = AsyncMock(return_value=created_task)

        response = app_client.post("/async-predict", json={"item_id": 5})

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == 123
    assert data["status"] == "pending"
    assert data["message"] == "Moderation request accepted"

    kafka_mock.send_moderation_request.assert_awaited_once_with(5, "moderation", 1, 3, 5)
    redis_client.set.assert_awaited_once_with(123, created_task)

@pytest.mark.anyio
async def test_worker_processes_message_successfully():
    moderationService = AsyncMock()
    moderationResultRepository = AsyncMock()
    kafkaClient = AsyncMock()

    # simplePredict возвращает (is_violation, proba)
    moderationService.simplePredict = AsyncMock(return_value=(True, 0.87))
    moderationResultRepository.update_moderation_result = AsyncMock()
    kafkaClient.send_moderation_request = AsyncMock()

    moderationConsumer = ModerationConsumer(
        server="localhost:9092",
        mainTopic="moderation",
        retryTopic="retry_moderation",
        moderationService=moderationService,
        moderationResultRepository=moderationResultRepository,
        kafkaClient=kafkaClient,
    )

    payload = {
        "item_id": 123,
        "attempt": 1,
        "max_attempts": 3,
        "retry_delay_seconds": 5,
    }
    fake_msg = FakeMsg(value=json.dumps(payload).encode("utf-8"))

    # создаём фейковы консьюмер
    moderationConsumer.consumer = FakeConsumer([fake_msg])

    await moderationConsumer.run()


    moderationService.simplePredict.assert_awaited_once()
    moderationResultRepository.update_moderation_result.assert_awaited_once_with(
        123, True, 0.87, "completed"
    )

    # assert: retry не трогали
    kafkaClient.send_moderation_request.assert_not_awaited()

    # assert: commit был
    moderationConsumer.consumer.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_worker_sends_to_retry_on_error():
    moderationService = AsyncMock()
    moderationResultRepository = AsyncMock()
    kafkaClient = AsyncMock()

    # форсим ошибку в simplePredict
    moderationService.simplePredict = AsyncMock(side_effect=RuntimeError("ML down"))
    moderationResultRepository.update_moderation_result = AsyncMock()
    kafkaClient.send_moderation_request = AsyncMock()

    moderationConsumer = ModerationConsumer(
        server="localhost:9092",
        mainTopic="moderation",
        retryTopic="retry_moderation",
        moderationService=moderationService,
        moderationResultRepository=moderationResultRepository,
        kafkaClient=kafkaClient,
    )

    payload = {
        "item_id": 123,
        "attempt": 1,
        "max_attempts": 3,
        "retry_delay_seconds": 5,
    }
    fake_msg = FakeMsg(value=json.dumps(payload).encode("utf-8"))
    moderationConsumer.consumer = FakeConsumer([fake_msg])
    await moderationConsumer.run()

    # assert: completed update не должно быть
    moderationResultRepository.update_moderation_result.assert_not_awaited()

    # assert: отправили в retry с attempt+1 и error_message=str(e)
    kafkaClient.send_moderation_request.assert_awaited_once()
    args, kwargs = kafkaClient.send_moderation_request.await_args

    # args: (item_id, topic, attempt, max_attempts, retry_delay_seconds, error_message)
    assert args[0] == 123
    assert args[1] == "retry_moderation"
    assert args[2] == 2
    assert args[3] == 3
    assert args[4] == 5
    assert "ML down" in args[5]

    # commit был
    moderationConsumer.consumer.commit.assert_awaited_once()



@pytest.mark.anyio
async def test_worker_sends_to_dlq(monkeypatch):
    # не ждём delay
    async def _no_sleep(_):
        return None
    monkeypatch.setattr("asyncio.sleep", _no_sleep)

    kafkaClient = AsyncMock()
    kafkaClient.send_moderation_request = AsyncMock()

    moderationResultRepository = AsyncMock()
    moderationResultRepository.update_moderation_result = AsyncMock()

    worker = RetryModerationConsumer(
        server="localhost:9092",
        mainTopic="moderation",
        retryTopic="retry_moderation",
        dlqTopic="dlq_moderation",
        kafkaClient=kafkaClient,
        moderationResultRepository=moderationResultRepository,
    )

    # attempt 1..4 при max_attempts=3
    base = {
        "item_id": 123,
        "max_attempts": 3,
        "retry_delay_seconds": 5,
        "error_message": "ML down",
    }

    messages = [
        FakeMsg(json.dumps({**base, "attempt": 1}).encode("utf-8")),
        FakeMsg(json.dumps({**base, "attempt": 2}).encode("utf-8")),
        FakeMsg(json.dumps({**base, "attempt": 3}).encode("utf-8")),
        FakeMsg(json.dumps({**base, "attempt": 4}).encode("utf-8")),
    ]
    worker.consumer = FakeConsumer(messages)
    await worker.run()

    # assert: отправка обратно в mainTopic 3 раза (attempt 1..3)
    expected_main_calls = [
        call(123, "moderation", 1, 3, 5),
        call(123, "moderation", 2, 3, 5),
        call(123, "moderation", 3, 3, 5),
    ]

    # все вызовы send_moderation_request
    all_calls = kafkaClient.send_moderation_request.await_args_list

    # первые 3 - в mainTopic
    assert [c.args for c in all_calls[:3]] == [c.args for c in expected_main_calls]

    # 4-й — DLQ
    assert all_calls[3].args == (123, "dlq_moderation", 4, 3, 5, "ML down")

    # assert: БД обновили failed ровно 1 раз (на attempt 4)
    moderationResultRepository.update_moderation_result.assert_awaited_once_with(
        123, None, None, "failed", "ML down"
    )

    # commit на каждое сообщение
    assert worker.consumer.commit.await_count == 4