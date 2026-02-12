from repositories.moderation import ModerationRepository
from services.exceptions import ItemNotFoundError
import traceback

class AsyncModerationService:
  def __init__(self, kafka=None):
    self.kafka = kafka
  async def prepare_data_for_moderation(self, item_id: int) -> int:
    moderationRepository = ModerationRepository()
    adv_existance = await moderationRepository.check_adv_existance(item_id)
    if adv_existance == False:
      raise ItemNotFoundError
    
    task_id = await moderationRepository.create_moderation_result(item_id)
    try:
      await self.kafka.send_moderation_request(item_id, "moderation", 1, 3, 5)
    except Exception as e:
        traceback.print_exc()
        
    return task_id
  
  async def get_moderation_result(self, task_id: int) -> tuple[int, str, bool, float, str | None]:
    moderationRepository = ModerationRepository()
    moderation_task_result = await moderationRepository.get_moderation_result(task_id)
    if moderation_task_result is None:
      raise ItemNotFoundError
    return (
        moderation_task_result["task_id"],
        moderation_task_result["status"],
        moderation_task_result["is_violation"],
        moderation_task_result["probability"],
        moderation_task_result["error_message"]
    )
    
    