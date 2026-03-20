import os
import asyncpg
from typing import Optional


class PostgresConnection:
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def create_pool(cls) -> asyncpg.Pool:
        if cls._pool is None or cls._pool._closed:
            cls._pool = await asyncpg.create_pool(
                user=os.getenv("POSTGRES_USER", "admin"),
                password=os.getenv("POSTGRES_PASSWORD", "password"),
                database=os.getenv("POSTGRES_DB", "moderation"),
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                min_size=1,
                max_size=10,
            )
        return cls._pool

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None or cls._pool._closed:
            return await cls.create_pool()
        return cls._pool

    @classmethod
    async def close_pool(cls) -> None:
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None