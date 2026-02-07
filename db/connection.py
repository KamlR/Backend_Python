import asyncpg
from typing import Optional


class PostgresConnection:
    _conn: Optional[asyncpg.Connection] = None

    @classmethod
    async def get(cls) -> asyncpg.Connection:
        """
        Возвращает одно и то же соединение.
        Если его нет или оно закрыто - создаёт заново.
        """
        if cls._conn is None or cls._conn.is_closed():
            cls._conn = await asyncpg.connect(
                user='admin',
                password='password',
                database='moderation',
                host='localhost',
                port=5432
            )

        return cls._conn

    @classmethod
    async def close(cls) -> None:
        if cls._conn and not cls._conn.is_closed():
            await cls._conn.close()
            cls._conn = None
