from typing import Any, Optional

from db.connection import PostgresConnection
from repositories.constants import (
    DB_QUERY_DELETE,
    DB_QUERY_INSERT,
    DB_QUERY_SELECT,
    DB_QUERY_UPDATE,
)
from repositories.metrics_context_manager import measure_db_query


class ModerationResultRepository:
    async def create_moderation_result(self, item_id: int) -> Optional[dict[str, Any]]:
        pool = await PostgresConnection.get_pool()

        query = """
        INSERT INTO public.moderation_results (
            item_id,
            status
        )
        VALUES ($1, 'pending')
        RETURNING task_id,
                  status,
                  is_violation,
                  probability,
                  error_message;
        """

        async with measure_db_query(DB_QUERY_INSERT):
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, item_id)

        return dict(row)

    async def get_moderation_result(self, task_id: int) -> Optional[dict[str, Any]]:
        query = """
        SELECT task_id, status, is_violation, probability, error_message
        FROM public.moderation_results
        WHERE task_id = $1
        """

        pool = await PostgresConnection.get_pool()

        async with measure_db_query(DB_QUERY_SELECT):
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, task_id)

        return dict(row) if row else None

    async def update_moderation_result(
        self,
        item_id: int,
        is_violation: bool,
        proba: float,
        status: str,
        error_message: str = None,
    ):
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

        pool = await PostgresConnection.get_pool()

        async with measure_db_query(DB_QUERY_UPDATE):
            async with pool.acquire() as conn:
                await conn.fetchrow(query, item_id, is_violation, proba, status, error_message)

    async def get_task_status(self, item_id: int) -> tuple[bool, str | None]:
        pool = await PostgresConnection.get_pool()

        query = """
        SELECT status
        FROM moderation_results
        WHERE item_id = $1
        LIMIT 1;
        """

        async with measure_db_query(DB_QUERY_SELECT):
            async with pool.acquire() as conn:
                status = await conn.fetchval(query, item_id)

        return status is not None, status

    async def delete_task(self, item_id: int) -> int | None:
        pool = await PostgresConnection.get_pool()

        query = """
        DELETE FROM public.moderation_results
        WHERE item_id = $1
        RETURNING task_id;
        """

        async with measure_db_query(DB_QUERY_DELETE):
            async with pool.acquire() as conn:
                task_id = await conn.fetchval(query, item_id)

        return task_id