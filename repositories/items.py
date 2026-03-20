from typing import Any, Optional

from db.connection import PostgresConnection
from schemas.item import ItemCreate
from repositories.constants import DB_QUERY_DELETE, DB_QUERY_INSERT, DB_QUERY_SELECT
from repositories.metrics_context_manager import measure_db_query


class ItemRepository:
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

        pool = await PostgresConnection.get_pool()

        async with measure_db_query(DB_QUERY_SELECT):
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, item_id)

        return dict(row) if row else None

    """
    Создание объявления.
    """
    async def create_item(self, item: ItemCreate) -> int:
        pool = await PostgresConnection.get_pool()

        query = """
        INSERT INTO public.items (seller_id, name, description, category, images_qty)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING item_id
        """

        async with measure_db_query(DB_QUERY_INSERT):
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    item.seller_id,
                    item.name,
                    item.description,
                    item.category,
                    item.images_qty,
                )

        return int(row["item_id"])

    async def check_adv_existance(self, item_id: int) -> bool:
        pool = await PostgresConnection.get_pool()

        query = """
        SELECT EXISTS (
            SELECT 1
            FROM public.items
            WHERE item_id = $1
        );
        """

        async with measure_db_query(DB_QUERY_SELECT):
            async with pool.acquire() as conn:
                result = await conn.fetchval(query, item_id)

        return bool(result)

    async def delete_item(self, item_id: int) -> bool:
        pool = await PostgresConnection.get_pool()

        query = """
        DELETE FROM public.items
        WHERE item_id = $1
        RETURNING item_id;
        """

        async with measure_db_query(DB_QUERY_DELETE):
            async with pool.acquire() as conn:
                result = await conn.fetchrow(query, item_id)

        return result is not None