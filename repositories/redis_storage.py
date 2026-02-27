import json
from dataclasses import dataclass
from typing import Any, Optional, Dict
from fastapi.encoders import jsonable_encoder

JsonDict = Dict[str, Any]

class RedisPredictionStorage:
    def __init__(self, redis_client, key_prefix, ttl_seconds):
      self.redis_client = redis_client
      self.key_prefix = key_prefix
      self.ttl_seconds = ttl_seconds

    def _key(self, object_id: int) -> str:
      return f"{self.key_prefix}:{object_id}"

    async def get(self, object_id: int) -> Optional[JsonDict]:
      raw = await self.redis_client.get(self._key(object_id))
      if raw is None:
          return None
      try:
          data = json.loads(raw)
          return data if isinstance(data, dict) else None
      except (ValueError, TypeError, json.JSONDecodeError):
          return None

    async def set(self, object_id: int, payload: JsonDict) -> JsonDict:
      safe_payload = jsonable_encoder(payload)
      await self.redis_client.set(
          self._key(object_id),
          json.dumps(safe_payload),
          ex=self.ttl_seconds,
      )
      return payload
    
    def change_key_prefix(self, new_key_prefix):
       self.key_prefix = new_key_prefix

    async def delete(self, object_id: int) -> None:
      await self.redis_client.delete(self._key(object_id))