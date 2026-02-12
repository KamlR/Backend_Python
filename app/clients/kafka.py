from typing import Optional
from datetime import datetime, timezone
import json
from dataclasses import dataclass

from aiokafka import AIOKafkaProducer

class KafkaClient:
  def __init__(self, server):
    self._server = server
    self._producer: Optional[AIOKafkaProducer] = None

  async def start(self) -> None:
    self._producer = AIOKafkaProducer(
        bootstrap_servers=self._server
    )
    await self._producer.start()

  async def stop(self) -> None:
    if self._producer:
      await self._producer.stop()
      self._producer = None
  
  async def send_moderation_request(self, item_id, moderation_topic, attempt, max_attempts, retry_delay_seconds, error_message = None) -> None:
    if not self._producer:
      raise RuntimeError("KafkaClient is not started")
    payload = {
        "item_id": item_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attempt": attempt,
        "max_attempts": max_attempts,
        "retry_delay_seconds": retry_delay_seconds,
        "error_message": error_message
    }

    value = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    key = str(item_id).encode("utf-8")  

    await self._producer.send_and_wait(
        topic=moderation_topic,
        key=key,
        value=value,
    )
    
  