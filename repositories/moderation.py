from typing import Any, Optional
from db.connection import PostgresConnection 
from schemas.user import UserCreate
from schemas.item import ItemCreate


class ModerationRepository:
    
    """
    Получение объекта на основании item_id для использования в модели.
    """
    async def get_item_for_prediction(self, item_id: int) -> Optional[dict[str, Any]]:
      sql = """
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
      row = await conn.fetchrow(sql, item_id)

      return dict(row) if row else None
  

    """
    Создание пользователя.
    """
    async def create_user(self, user: UserCreate) -> int:
      conn = await PostgresConnection.get()

      sql = """
        INSERT INTO public.users (first_name, last_name, is_verified_seller)
        VALUES ($1, $2, $3)
        RETURNING seller_id
        """
      row = await conn.fetchrow(sql, user.first_name, user.last_name, user.is_verified_seller)
      return int(row["seller_id"])
    

    """
    Создание объявления.
    """
    async def create_item(self, item: ItemCreate) -> int:
      conn = await PostgresConnection.get()
      sql = """
        INSERT INTO public.items (seller_id, name, description, category, images_qty)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING item_id
        """
      row = await conn.fetchrow(
          sql, item.seller_id, item.name, item.description, item.category, item.images_qty
      )
      return int(row["item_id"])

