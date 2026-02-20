# app/workers/moderation_worker.py

import asyncio
from aiokafka import AIOKafkaConsumer
import json
from model import load_model
from services.moderation import ModerationService
from schemas.predict import SimplePredictAdvIn
from repositories.moderation_results import ModerationResultRepository
from app.clients.kafka import KafkaClient

class ModerationConsumer:
    def __init__(self, server, mainTopic, retryTopic, moderationService,  moderationResultRepository, kafkaClient):
        self.server = server
        self.mainTopic = mainTopic
        self.retryTopic = retryTopic
        self.consumer: AIOKafkaConsumer | None = None
        self.moderationService = moderationService
        self.moderationResultRepository =  moderationResultRepository
        self.kafkaClient = kafkaClient

    async def start(self) -> None:
        self.consumer = AIOKafkaConsumer(
            self.mainTopic,
            bootstrap_servers=self.server,
            enable_auto_commit=False,
            group_id="moderation-workers"
        )
        await self.consumer.start()

    async def stop(self) -> None:
        if self.consumer:
            await self.consumer.stop()

    async def run(self) -> None:
        if not self.consumer:
            raise RuntimeError("Consumer not started")

        print("Worker started, waiting for messages...")

        try:
            async for msg in self.consumer:
                print(f"[worker] received raw message: {msg.value}")
                try:
                    data = json.loads(msg.value.decode("utf-8"))
                    item_id = int(data.get("item_id"))
                    is_violation, proba = await self.moderationService.simplePredict(SimplePredictAdvIn(item_id=item_id))
                    await self.moderationResultRepository.update_moderation_result(item_id, is_violation, proba, "completed")
                except Exception as e:
                    await self.kafkaClient.send_moderation_request(item_id, self.retryTopic, int(data.get("attempt")) + 1,  int(data.get("max_attempts")), int(data.get("retry_delay_seconds")), str(e))
                finally:
                    await self.consumer.commit()
        finally:
            await self.stop()


async def main() -> None:
    model = None
    while model is None:
        model = load_model()
    moderationService = ModerationService(model)
    moderationResultRepository = ModerationResultRepository()
    kafkaClient = KafkaClient("localhost:9092")
    await kafkaClient.start()
    moderationConsumer = ModerationConsumer("localhost:9092", "moderation", "retry_moderation", moderationService, moderationResultRepository, kafkaClient)
    await moderationConsumer.start()
    await moderationConsumer.run()


if __name__ == "__main__":
    asyncio.run(main())
