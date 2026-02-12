# app/workers/moderation_worker.py

import asyncio
from aiokafka import AIOKafkaConsumer
import json
from repositories.moderation import ModerationRepository
from app.clients.kafka import KafkaClient


class RetryModerationConsumer:
    def __init__(self, server, mainTopic, retryTopic, dlqTopic, kafkaClient, moderationRepository):
        self.server = server
        self.mainTopic = mainTopic
        self.retryTopic = retryTopic
        self.dlqTopic = dlqTopic
        self.kafkaClient = kafkaClient
        self.moderationRepository = moderationRepository
        self.consumer: AIOKafkaConsumer | None = None

    async def start(self) -> None:
        self.consumer = AIOKafkaConsumer(
            self.retryTopic,
            bootstrap_servers=self.server,
            group_id="retry-moderation-workers",
            enable_auto_commit=False,
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
                data = json.loads(msg.value.decode("utf-8"))
                item_id = int(data.get("item_id"))
                attempt = int(data.get("attempt"))
                max_attempts = int(data.get("max_attempts"))
                delay = int(data.get("retry_delay_seconds"))
                error_message = data.get("error_message")
                await asyncio.sleep(delay)

                if attempt <= max_attempts:
                    await self.kafkaClient.send_moderation_request(int(data.get("item_id")), self.mainTopic, int(data.get("attempt")),  int(data.get("max_attempts")), int(data.get("retry_delay_seconds")))
                else:
                    await self.moderationRepository.update_moderation_result(item_id, None, None, "failed", error_message)
                    await self.kafkaClient.send_moderation_request(int(data.get("item_id")), self.dlqTopic, int(data.get("attempt")),  int(data.get("max_attempts")), int(data.get("retry_delay_seconds")), error_message)
                await self.consumer.commit()
        finally:
            
            await self.stop()


async def main() -> None:
    moderationRepository = ModerationRepository()
    kafkaClient = KafkaClient("localhost:9092")
    await kafkaClient.start()
    retryModerationConsumer = RetryModerationConsumer("localhost:9092", "moderation", "retry_moderation", "dlq_moderation", kafkaClient, moderationRepository)
    await retryModerationConsumer.start()
    await retryModerationConsumer.run()


if __name__ == "__main__":
    asyncio.run(main())
