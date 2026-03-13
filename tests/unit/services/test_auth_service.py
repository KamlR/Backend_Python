from unittest.mock import AsyncMock
import pytest

from services.auth import AuthService
from errors.auth_exceptions import (
    InvalidCredentialsError,
    AccountBlockedError,
    InvalidTokenError,
    AccountNotFoundError,
)


@pytest.mark.asyncio
async def test_login_success():
    repo = AsyncMock()
    repo.get_account_by_login_and_password.return_value = {
        "id": 1,
        "login": "karina",
        "password": "123",
        "is_blocked": False,
    }

    service = AuthService(
        account_repository=repo,
        jwt_secret="test_secret",
    )

    result = await service.login("karina", "123")

    assert result["id"] == 1
    assert result["login"] == "karina"


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    repo = AsyncMock()
    repo.get_account_by_login_and_password.return_value = None

    service = AuthService(
        account_repository=repo,
        jwt_secret="test_secret",
    )

    with pytest.raises(InvalidCredentialsError):
        await service.login("karina", "wrong_password")


@pytest.mark.asyncio
async def test_login_blocked_account():
    repo = AsyncMock()
    repo.get_account_by_login_and_password.return_value = {
        "id": 1,
        "login": "karina",
        "password": "123",
        "is_blocked": True,
    }

    service = AuthService(
        account_repository=repo,
        jwt_secret="test_secret",
    )

    with pytest.raises(AccountBlockedError):
        await service.login("karina", "123")


def test_create_and_verify_access_token():
    repo = AsyncMock()

    service = AuthService(
        account_repository=repo,
        jwt_secret="test_secret",
    )

    account = {
        "id": 1,
        "login": "karina",
        "password": "123",
        "is_blocked": False,
    }

    token = service.create_access_token(account)
    payload = service.verify_access_token(token)

    assert payload["sub"] == "1"
    assert payload["login"] == "karina"


def test_verify_access_token_invalid():
    repo = AsyncMock()

    service = AuthService(
        account_repository=repo,
        jwt_secret="test_secret",
    )

    with pytest.raises(InvalidTokenError):
        service.verify_access_token("invalid_token")


@pytest.mark.asyncio
async def test_get_account_from_token_success():
    repo = AsyncMock()

    service = AuthService(
        account_repository=repo,
        jwt_secret="test_secret",
    )

    account = {
        "id": 1,
        "login": "karina",
        "password": "123",
        "is_blocked": False,
    }

    token = service.create_access_token(account)
    repo.get_account_by_id.return_value = account

    result = await service.get_account_from_token(token)

    assert result["id"] == 1
    assert result["login"] == "karina"


@pytest.mark.asyncio
async def test_get_account_from_token_not_found():
    repo = AsyncMock()

    service = AuthService(
        account_repository=repo,
        jwt_secret="test_secret",
    )

    account = {
        "id": 1,
        "login": "karina",
        "password": "123",
        "is_blocked": False,
    }

    token = service.create_access_token(account)
    repo.get_account_by_id.return_value = None

    with pytest.raises(AccountNotFoundError):
        await service.get_account_from_token(token)


@pytest.mark.asyncio
async def test_get_account_from_token_blocked():
    repo = AsyncMock()

    service = AuthService(
        account_repository=repo,
        jwt_secret="test_secret",
    )

    token = service.create_access_token(
        {
            "id": 1,
            "login": "karina",
            "password": "123",
            "is_blocked": False,
        }
    )

    repo.get_account_by_id.return_value = {
        "id": 1,
        "login": "karina",
        "password": "123",
        "is_blocked": True,
    }

    with pytest.raises(AccountBlockedError):
        await service.get_account_from_token(token)