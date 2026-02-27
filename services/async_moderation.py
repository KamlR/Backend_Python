from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultRepository
from services.exceptions import ItemNotFoundError
import traceback

class AsyncModerationService:
  def __init__(self, redisPredictionStorage, kafka=None):
    self.kafka = kafka
    self.redisPredictionStorage = redisPredictionStorage
  async def prepare_data_for_moderation(self, item_id: int) -> int:
    itemRepository = ItemRepository()
    moderestionResultRepo = ModerationResultRepository()
    adv_existance = await itemRepository.check_adv_existance(item_id)
    if adv_existance == False:
      raise ItemNotFoundError
    
    created_task = await moderestionResultRepo.create_moderation_result(item_id)
    try:
      await self.redisPredictionStorage.set(created_task["task_id"], created_task)
    except Exception as e:
      print(e)
    try:
      await self.kafka.send_moderation_request(item_id, "moderation", 1, 3, 5)
    except Exception as e:
        traceback.print_exc()
        
    return created_task["task_id"]
  
  async def get_moderation_result(self, task_id: int) -> tuple[int, str, bool, float, str | None]:
    cached = await self.redisPredictionStorage.get(task_id)
    if cached is not None:
      return (
        cached["task_id"],
        cached["status"],
        cached["is_violation"],
        cached["probability"],
        cached["error_message"]
    )
    moderestionResultRepo = ModerationResultRepository()
    moderation_task_result = await moderestionResultRepo.get_moderation_result(task_id)
    if moderation_task_result is None:
      raise ItemNotFoundError
    await self.redisPredictionStorage.set(task_id, moderation_task_result)
    return (
        moderation_task_result["task_id"],
        moderation_task_result["status"],
        moderation_task_result["is_violation"],
        moderation_task_result["probability"],
        moderation_task_result["error_message"]
    )
    
    