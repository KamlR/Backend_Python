import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from db.connection import PostgresConnection
from main import app as fastapi_app


class FakeModel:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, X):
        return [[1 - self.probability, self.probability]]

@pytest.fixture
def app():
    return fastapi_app

# для синхронных тестов
@pytest.fixture
def app_client(app):
    return TestClient(app)


# для async тестов
@pytest.fixture
async def async_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def allow_model():
    return FakeModel(probability=0.8)  # нарушение = True


@pytest.fixture
def deny_model():
    return FakeModel(probability=0.1)  # нарушение = False


@pytest.fixture
async def test_item():
    conn = await PostgresConnection.get()

    # создаём юзера
    seller_id = await conn.fetchval("""
        INSERT INTO public.users (first_name, last_name, is_verified_seller)
        VALUES ('Test', 'User', TRUE)
        RETURNING seller_id
    """)

    # создаём item
    item_id = await conn.fetchval("""
        INSERT INTO public.items
            (seller_id, name, description, category, images_qty)
        VALUES
            ($1, 'Bad item', 'spam text', 10, 2)
        RETURNING item_id
    """, seller_id)

    yield item_id   


    await conn.execute("DELETE FROM public.items WHERE item_id = $1", item_id)
    await conn.execute("DELETE FROM public.users WHERE seller_id = $1", seller_id)
    await conn.close()
