import pytest

from repositories.account import AccountRepository
from db.connection import PostgresConnection


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_account():
    repo = AccountRepository()
    login = "new_user"
    password = "123456"

    account_id = await repo.create_account(login, password)

    assert isinstance(account_id, int)

    conn = await PostgresConnection.get()
    row = await conn.fetchrow(
        """
        SELECT id, login, password, is_blocked
        FROM public.account
        WHERE id = $1
        """,
        account_id,
    )

    assert row is not None
    assert row["id"] == account_id
    assert row["login"] == login
    assert row["password"] == AccountRepository.hash_password(password)
    assert row["is_blocked"] is False

    await conn.execute("DELETE FROM public.account WHERE id = $1", account_id)
    await conn.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_account_by_id(test_account):
    repo = AccountRepository()

    result = await repo.get_account_by_id(test_account["id"])

    assert result is not None
    assert result["id"] == test_account["id"]
    assert result["login"] == test_account["login"]
    assert result["password"] == test_account["hashed_password"]
    assert result["is_blocked"] is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_account_by_id_not_found():
    repo = AccountRepository()

    result = await repo.get_account_by_id(999999)

    assert result is None

    conn = await PostgresConnection.get()
    await conn.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_account_by_login_and_password_success(test_account):
    repo = AccountRepository()

    result = await repo.get_account_by_login_and_password(
        test_account["login"],
        test_account["password"],
    )

    assert result is not None
    assert result["id"] == test_account["id"]
    assert result["login"] == test_account["login"]
    assert result["password"] == test_account["hashed_password"]
    assert result["is_blocked"] is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_account_by_login_and_password_wrong_password(test_account):
    repo = AccountRepository()

    result = await repo.get_account_by_login_and_password(
        test_account["login"],
        "wrong_password",
    )
    assert result is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_account(test_account):
    repo = AccountRepository()

    result = await repo.delete_account(test_account["id"])

    assert result is True

    conn = await PostgresConnection.get()
    row = await conn.fetchrow(
        "SELECT id FROM public.account WHERE id = $1",
        test_account["id"],
    )
    assert row is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_account_not_found():
    repo = AccountRepository()

    result = await repo.delete_account(999999)

    assert result is False

    conn = await PostgresConnection.get()
    await conn.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_block_account(test_account):
    repo = AccountRepository()

    result = await repo.block_account(test_account["id"])

    assert result is True

    conn = await PostgresConnection.get()
    is_blocked = await conn.fetchval(
        "SELECT is_blocked FROM public.account WHERE id = $1",
        test_account["id"],
    )
    assert is_blocked is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_block_account_not_found():
    repo = AccountRepository()

    result = await repo.block_account(999999)

    assert result is False

    conn = await PostgresConnection.get()
    await conn.close()
    

