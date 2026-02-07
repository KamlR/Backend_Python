import pytest

from db.connection import PostgresConnection
from repositories.moderation import ModerationRepository 
from schemas.user import UserCreate
from schemas.item import ItemCreate


@pytest.mark.asyncio
async def test_create_user_inserts_row():
    repo = ModerationRepository()
    conn = await PostgresConnection.get()

    user = UserCreate(
        first_name="Repo",
        last_name="Test",
        is_verified_seller=True,
    )

    seller_id = await repo.create_user(user)
    assert isinstance(seller_id, int)
    assert seller_id > 0

    row = await conn.fetchrow(
        """
        SELECT seller_id, first_name, last_name, is_verified_seller
        FROM public.users
        WHERE seller_id = $1
        """,
        seller_id,
    )

    assert row is not None
    assert row["seller_id"] == seller_id
    assert row["first_name"] == user.first_name
    assert row["last_name"] == user.last_name
    assert row["is_verified_seller"] == user.is_verified_seller


    await conn.execute("DELETE FROM public.users WHERE seller_id = $1", seller_id)
    await conn.close()


@pytest.mark.asyncio
async def test_create_item_inserts_row_and_get_item_for_prediction():
    repo = ModerationRepository()
    conn = await PostgresConnection.get()

    # 1) подготовка: создаём продавца
    seller_id = await conn.fetchval(
        """
        INSERT INTO public.users (first_name, last_name, is_verified_seller)
        VALUES ('Item', 'Owner', TRUE)
        RETURNING seller_id
        """
    )

    try:
        # 2) создаём item через репозиторий
        item = ItemCreate(
            seller_id=seller_id,
            name="Bad item",
            description="spam text",
            category=10,
            images_qty=2,
        )

        item_id = await repo.create_item(item)
        assert isinstance(item_id, int)
        assert item_id > 0

        # 3) проверяем, что запись реально появилась
        row = await conn.fetchrow(
            """
            SELECT item_id, seller_id, name, description, category, images_qty
            FROM public.items
            WHERE item_id = $1
            """,
            item_id,
        )
        assert row is not None
        assert row["item_id"] == item_id
        assert row["seller_id"] == seller_id
        assert row["name"] == item.name
        assert row["description"] == item.description
        assert row["category"] == item.category
        assert row["images_qty"] == item.images_qty

        # 4) проверяем get_item_for_prediction (join с users)
        dto = await repo.get_item_for_prediction(item_id)
        assert dto is not None
        assert dto["item_id"] == item_id
        assert dto["seller_id"] == seller_id
        assert dto["name"] == item.name
        assert dto["description"] == item.description
        assert dto["category"] == item.category
        assert dto["images_qty"] == item.images_qty
        assert dto["is_verified_seller"] is True

        # cleanup item
        await conn.execute("DELETE FROM public.items WHERE item_id = $1", item_id)

    finally:
        # cleanup user
        await conn.execute("DELETE FROM public.users WHERE seller_id = $1", seller_id)
        await conn.close()