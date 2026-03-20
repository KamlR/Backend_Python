import uuid

import fakeredis.aioredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from db.connection import PostgresConnection
from main import app as fastapi_app
from repositories.account import AccountRepository
from dependencies.auth import get_current_account


class FakeModel:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, X):
        return [[1 - self.probability, self.probability]]


@pytest_asyncio.fixture
async def redis_client():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


@pytest.fixture
def app():
    async def override_get_current_account():
        return {
            "id": 1,
            "login": "test_user",
            "is_blocked": False,
        }

    fastapi_app.dependency_overrides[get_current_account] = override_get_current_account
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def app_client(app):
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def allow_model():
    return FakeModel(probability=0.8)


@pytest.fixture
def deny_model():
    return FakeModel(probability=0.1)


@pytest_asyncio.fixture
async def db_pool():
    pool = await PostgresConnection.create_pool()
    yield pool
    await PostgresConnection.close_pool()


@pytest_asyncio.fixture
async def test_item(db_pool):
    async with db_pool.acquire() as conn:
        seller_id = await conn.fetchval(
            """
            INSERT INTO public.users (first_name, last_name, is_verified_seller)
            VALUES ('Test', 'User', TRUE)
            RETURNING seller_id
            """
        )

        item_id = await conn.fetchval(
            """
            INSERT INTO public.items
                (seller_id, name, description, category, images_qty)
            VALUES
                ($1, 'Bad item', 'spam text', 10, 2)
            RETURNING item_id
            """,
            seller_id,
        )

    yield item_id

    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM public.items WHERE item_id = $1",
            item_id,
        )
        await conn.execute(
            "DELETE FROM public.users WHERE seller_id = $1",
            seller_id,
        )


@pytest_asyncio.fixture
async def test_account(db_pool):
    login = f"test_login_{uuid.uuid4().hex}"
    password = "test_password"
    hashed_password = AccountRepository.hash_password(password)

    async with db_pool.acquire() as conn:
        account_id = await conn.fetchval(
            """
            INSERT INTO public.account (login, password, is_blocked)
            VALUES ($1, $2, FALSE)
            RETURNING id
            """,
            login,
            hashed_password,
        )

    yield {
        "id": account_id,
        "login": login,
        "password": password,
        "hashed_password": hashed_password,
        "is_blocked": False,
    }

    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM public.account WHERE id = $1",
            account_id,
        )