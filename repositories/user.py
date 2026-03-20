from db.connection import PostgresConnection
from schemas.user import UserCreate
from repositories.constants import DB_QUERY_INSERT
from repositories.metrics_context_manager import measure_db_query


class UserRepository:
    """
    Создание пользователя.
    """
    async def create_user(self, user: UserCreate) -> int:
        pool = await PostgresConnection.get_pool()

        query = """
        INSERT INTO public.users (first_name, last_name, is_verified_seller)
        VALUES ($1, $2, $3)
        RETURNING seller_id
        """

        async with measure_db_query(DB_QUERY_INSERT):
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    user.first_name,
                    user.last_name,
                    user.is_verified_seller,
                )

        return int(row["seller_id"])