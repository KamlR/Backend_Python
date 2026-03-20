from typing import Any, Optional
import hashlib

from db.connection import PostgresConnection
from repositories.constants import (
    DB_QUERY_DELETE,
    DB_QUERY_INSERT,
    DB_QUERY_SELECT,
    DB_QUERY_UPDATE,
)
from repositories.metrics_context_manager import measure_db_query


class AccountRepository:
    """
    Создание аккаунта.
    """
    async def create_account(self, login: str, password: str) -> int:
        pool = await PostgresConnection.get_pool()
        hashed_password = AccountRepository.hash_password(password)

        query = """
        INSERT INTO public.account (login, password)
        VALUES ($1, $2)
        RETURNING id
        """

        async with measure_db_query(DB_QUERY_INSERT):
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, login, hashed_password)

        return int(row["id"])

    """
    Получение аккаунта по id.
    """
    async def get_account_by_id(self, account_id: int) -> Optional[dict[str, Any]]:
        pool = await PostgresConnection.get_pool()

        query = """
        SELECT id, login, password, is_blocked
        FROM public.account
        WHERE id = $1
        """

        async with measure_db_query(DB_QUERY_SELECT):
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, account_id)

        return dict(row) if row else None

    """
    Получение аккаунта по логину и паролю.
    """
    async def get_account_by_login_and_password(
        self,
        login: str,
        password: str,
    ) -> Optional[dict[str, Any]]:
        pool = await PostgresConnection.get_pool()
        hashed_password = AccountRepository.hash_password(password)

        query = """
        SELECT id, login, password, is_blocked
        FROM public.account
        WHERE login = $1 AND password = $2
        """

        async with measure_db_query(DB_QUERY_SELECT):
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, login, hashed_password)

        return dict(row) if row else None

    """
    Проверка существования аккаунта.
    """
    async def check_account_existence(self, account_id: int) -> bool:
        pool = await PostgresConnection.get_pool()

        query = """
        SELECT EXISTS (
            SELECT 1
            FROM public.account
            WHERE id = $1
        );
        """

        async with measure_db_query(DB_QUERY_SELECT):
            async with pool.acquire() as conn:
                result = await conn.fetchval(query, account_id)

        return bool(result)

    """
    Удаление аккаунта.
    """
    async def delete_account(self, account_id: int) -> bool:
        pool = await PostgresConnection.get_pool()

        query = """
        DELETE FROM public.account
        WHERE id = $1
        RETURNING id
        """

        async with measure_db_query(DB_QUERY_DELETE):
            async with pool.acquire() as conn:
                result = await conn.fetchrow(query, account_id)

        return result is not None

    """
    Блокировка аккаунта.
    """
    async def block_account(self, account_id: int) -> bool:
        pool = await PostgresConnection.get_pool()

        query = """
        UPDATE public.account
        SET is_blocked = TRUE
        WHERE id = $1
        RETURNING id
        """

        async with measure_db_query(DB_QUERY_UPDATE):
            async with pool.acquire() as conn:
                result = await conn.fetchrow(query, account_id)

        return result is not None

    def hash_password(password: str) -> str:
        return hashlib.md5(password.encode("utf-8")).hexdigest()