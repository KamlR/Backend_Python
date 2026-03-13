from datetime import datetime, timedelta, UTC
from typing import Any
import jwt

from repositories.account import AccountRepository
from errors.auth_exceptions import (
    InvalidCredentialsError,
    AccountBlockedError,
    InvalidTokenError,
    AccountNotFoundError,
)


class AuthService:
    def __init__(
        self,
        account_repository: AccountRepository,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        token_expire_minutes: int = 60,
    ) -> None:
        self.account_repository = account_repository
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.token_expire_minutes = token_expire_minutes

    async def login(self, login: str, password: str) -> dict[str, Any]:
        account = await self.account_repository.get_account_by_login_and_password(
            login, password
        )

        if not account:
            raise InvalidCredentialsError("Invalid login or password")

        if account["is_blocked"]:
            raise AccountBlockedError("Account is blocked")

        return account

    def create_access_token(self, account: dict[str, Any]) -> str:
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.token_expire_minutes)

        payload = {
            "sub": str(account["id"]),
            "login": account["login"],
            "exp": expire,
            "iat": now,
        }

        return jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm,
        )

    def verify_access_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
            )
            return payload
        except jwt.PyJWTError as e:
            raise InvalidTokenError("Invalid token") from e

    async def get_account_from_token(self, token: str) -> dict[str, Any]:
        payload = self.verify_access_token(token)

        account_id_raw = payload.get("sub")
        if account_id_raw is None:
            raise InvalidTokenError("Token payload does not contain account id")

        try:
            account_id = int(account_id_raw)
        except ValueError as e:
            raise InvalidTokenError("Invalid account id in token") from e

        account = await self.account_repository.get_account_by_id(account_id)
        if not account:
            raise AccountNotFoundError("Account not found")

        if account["is_blocked"]:
            raise AccountBlockedError("Account is blocked")

        return account