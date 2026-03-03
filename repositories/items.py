from typing import Any, Optional
import time

from db.connection import PostgresConnection
from schemas.item import ItemCreate
from app.metrics.metrics import DB_QUERY_DURATION_SECONDS


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

        conn = await PostgresConnection.get()

        start = time.perf_counter()
        row = await conn.fetchrow(query, item_id)
        DB_QUERY_DURATION_SECONDS.labels(query_type="select").observe(
            time.perf_counter() - start
        )

        return dict(row) if row else None

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

        start = time.perf_counter()
        row = await conn.fetchrow(
            query,
            item.seller_id,
            item.name,
            item.description,
            item.category,
            item.images_qty,
        )
        DB_QUERY_DURATION_SECONDS.labels(query_type="insert").observe(
            time.perf_counter() - start
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

        start = time.perf_counter()
        result = await conn.fetchval(query, item_id)
        DB_QUERY_DURATION_SECONDS.labels(query_type="select").observe(
            time.perf_counter() - start
        )

        return bool(result)

    async def delete_item(self, item_id: int) -> bool:
        conn = await PostgresConnection.get()

        query = """
        DELETE FROM public.items
        WHERE item_id = $1
        RETURNING item_id;
        """

        start = time.perf_counter()
        result = await conn.fetchrow(query, item_id)
        DB_QUERY_DURATION_SECONDS.labels(query_type="delete").observe(
            time.perf_counter() - start
        )

        return result is not None