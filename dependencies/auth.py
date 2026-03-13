import os
from fastapi import Cookie, Depends, HTTPException, status
from repositories.account import AccountRepository
from services.auth import AuthService
from errors.auth_exceptions import (
    InvalidTokenError,
    AccountNotFoundError,
    AccountBlockedError,
)

JWT_SECRET = os.getenv("JWT_SECRET", "DEV_SECRET")

def get_account_repository() -> AccountRepository:
    return AccountRepository()


def get_auth_service(
    account_repository: AccountRepository = Depends(get_account_repository),
) -> AuthService:
    return AuthService(
        account_repository=account_repository,
        jwt_secret=JWT_SECRET,
        jwt_algorithm="HS256",
        token_expire_minutes=60,
    )


async def get_current_account(
    access_token: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        account = await auth_service.get_account_from_token(access_token)
        return account
    except (InvalidTokenError, AccountNotFoundError, AccountBlockedError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
        )