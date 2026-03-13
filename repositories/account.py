from typing import Any, Optional
import time
import hashlib

from db.connection import PostgresConnection
from app.metrics.metrics import DB_QUERY_DURATION_SECONDS


class AccountRepository:

    """
    Создание аккаунта.
    """
    async def create_account(self, login: str, password: str) -> int:
        conn = await PostgresConnection.get()
        hashed_password = AccountRepository.hash_password(password)

        query = """
        INSERT INTO public.account (login, password)
        VALUES ($1, $2)
        RETURNING id
        """

        start = time.perf_counter()
        row = await conn.fetchrow(query, login, hashed_password)
        DB_QUERY_DURATION_SECONDS.labels(query_type="insert").observe(
            time.perf_counter() - start
        )

        return int(row["id"])
    
    """
    Получение аккаунта по id.
    """
    async def get_account_by_id(self, account_id: int) -> Optional[dict[str, Any]]:
        conn = await PostgresConnection.get()

        query = """
        SELECT id, login, password, is_blocked
        FROM public.account
        WHERE id = $1
        """

        start = time.perf_counter()
        row = await conn.fetchrow(query, account_id)
        DB_QUERY_DURATION_SECONDS.labels(query_type="select").observe(
            time.perf_counter() - start
        )

        return dict(row) if row else None
    
    """
    Получение аккаунта по логину и паролю.
    """
    async def get_account_by_login_and_password(
        self,
        login: str,
        password: str
    ) -> Optional[dict[str, Any]]:
        conn = await PostgresConnection.get()
        hashed_password = AccountRepository.hash_password(password)
        query = """
        SELECT id, login, password, is_blocked
        FROM public.account
        WHERE login = $1 AND password = $2
        """

        start = time.perf_counter()
        row = await conn.fetchrow(query, login, hashed_password)
        DB_QUERY_DURATION_SECONDS.labels(query_type="select").observe(
            time.perf_counter() - start
        )

        return dict(row) if row else None


    """
    Проверка существования аккаунта.
    """
    async def check_account_existence(self, account_id: int) -> bool:
        conn = await PostgresConnection.get()

        query = """
        SELECT EXISTS (
            SELECT 1
            FROM public.account
            WHERE id = $1
        );
        """

        start = time.perf_counter()
        result = await conn.fetchval(query, account_id)
        DB_QUERY_DURATION_SECONDS.labels(query_type="select").observe(
            time.perf_counter() - start
        )

        return bool(result)
    
    """
    Удаление аккаунта.
    """
    async def delete_account(self, account_id: int) -> bool:
        conn = await PostgresConnection.get()

        query = """
        DELETE FROM public.account
        WHERE id = $1
        RETURNING id
        """

        start = time.perf_counter()
        result = await conn.fetchrow(query, account_id)
        DB_QUERY_DURATION_SECONDS.labels(query_type="delete").observe(
            time.perf_counter() - start
        )

        return result is not None
    
    """
    Блокировка аккаунта.
    """
    async def block_account(self, account_id: int) -> bool:
        conn = await PostgresConnection.get()

        query = """
        UPDATE public.account
        SET is_blocked = TRUE
        WHERE id = $1
        RETURNING id
        """

        start = time.perf_counter()
        result = await conn.fetchrow(query, account_id)
        DB_QUERY_DURATION_SECONDS.labels(query_type="update").observe(
            time.perf_counter() - start
        )

        return result is not None
    
    def hash_password(password: str) -> str:
        return hashlib.md5(password.encode("utf-8")).hexdigest()