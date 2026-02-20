from typing import Any, Optional
from db.connection import PostgresConnection 

class ModerationResultRepository:
    async def create_moderation_result(self, item_id: int) -> int:
      conn = await PostgresConnection.get()
      query = """
        INSERT INTO public.moderation_results (
            item_id,
            status
        )
        VALUES ($1, 'pending')
        RETURNING task_id;
          """

      task_id = await conn.fetchval(query, item_id)
      return task_id
    
    async def get_moderation_result(self, task_id: int) -> Optional[dict[str, Any]]:
      query = """
        SELECT task_id, status, is_violation, probability, error_message
        FROM public.moderation_results
        WHERE task_id = $1
        """
      conn = await PostgresConnection.get()
      row = await conn.fetchrow(query, task_id)
      return dict(row) if row else None
    
    async def update_moderation_result(self, item_id: int, is_violation: bool, proba: float, status: str, error_message: str = None):
      query = """
        UPDATE moderation_results
        SET
            is_violation = $2,
            probability = $3,
            status = $4,
            error_message = $5,
            processed_at = NOW()
        WHERE item_id = $1
    """
      conn = await PostgresConnection.get()
      await conn.fetchrow(query, item_id, is_violation, proba, status, error_message)