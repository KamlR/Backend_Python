from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException

from dependencies.auth import get_current_account
from errors.auth_exceptions import InvalidTokenError


@pytest.mark.asyncio
async def test_get_current_account_success():
    auth_service = AsyncMock()
    auth_service.get_account_from_token.return_value = {
        "id": 1,
        "login": "karina",
        "password": "123",
        "is_blocked": False,
    }

    result = await get_current_account(
        access_token="valid_token",
        auth_service=auth_service,
    )

    assert result["id"] == 1
    assert result["login"] == "karina"


@pytest.mark.asyncio
async def test_get_current_account_without_cookie():
    auth_service = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await get_current_account(
            access_token=None,
            auth_service=auth_service,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Authentication required"


@pytest.mark.asyncio
async def test_get_current_account_invalid_token():
    auth_service = AsyncMock()
    auth_service.get_account_from_token.side_effect = InvalidTokenError("Invalid token")

    with pytest.raises(HTTPException) as exc:
        await get_current_account(
            access_token="bad_token",
            auth_service=auth_service,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid or expired authentication credentials"