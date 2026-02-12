from typing import Any, Optional
from db.connection import PostgresConnection 
from schemas.user import UserCreate
from schemas.item import ItemCreate


class ModerationRepository:
    
    """
    Получение объекта на основании item_id для использования в модели.
    """
    async def get_item_for_prediction(self, item_id: int) -> Optional[dict[str, Any]]:
      query = """
        SELECT
            i.item_id,
            i.seller_id,
            i.name,
            i.description,
            i.category,
            i.images_qty,
            u.is_verified_seller
        FROM public.items i
        LEFT JOIN public.users u ON u.seller_id = i.seller_id
        WHERE i.item_id = $1
        """
      conn = await PostgresConnection.get()
      row = await conn.fetchrow(query, item_id)

      return dict(row) if row else None
  

    """
    Создание пользователя.
    """
    async def create_user(self, user: UserCreate) -> int:
      conn = await PostgresConnection.get()

      query = """
        INSERT INTO public.users (first_name, last_name, is_verified_seller)
        VALUES ($1, $2, $3)
        RETURNING seller_id
        """
      row = await conn.fetchrow(query, user.first_name, user.last_name, user.is_verified_seller)
      return int(row["seller_id"])
    

    """
    Создание объявления.
    """
    async def create_item(self, item: ItemCreate) -> int:
      conn = await PostgresConnection.get()
      query = """
        INSERT INTO public.items (seller_id, name, description, category, images_qty)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING item_id
        """
      row = await conn.fetchrow(
          query, item.seller_id, item.name, item.description, item.category, item.images_qty
      )
      return int(row["item_id"])
    
    async def check_adv_existance(self, item_id: int) -> bool:
      conn = await PostgresConnection.get()
      query = """
      SELECT EXISTS (
          SELECT 1
          FROM public.items
          WHERE item_id = $1
      );
      """
      result = await conn.fetchval(query, item_id)
      return bool(result)
        
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