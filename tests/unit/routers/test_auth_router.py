from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.auth import auth_router
from dependencies.auth import get_auth_service
from errors.auth_exceptions import InvalidCredentialsError, AccountBlockedError


class MockAuthServiceSuccess:
    async def login(self, login: str, password: str):
        return {
            "id": 1,
            "login": login,
            "password": password,
            "is_blocked": False,
        }

    def create_access_token(self, account: dict) -> str:
        return "test_jwt_token"


class MockAuthServiceInvalidCredentials:
    async def login(self, login: str, password: str):
        raise InvalidCredentialsError()

    def create_access_token(self, account: dict) -> str:
        return "test_jwt_token"


class MockAuthServiceBlocked:
    async def login(self, login: str, password: str):
        raise AccountBlockedError()

    def create_access_token(self, account: dict) -> str:
        return "test_jwt_token"


def create_test_app(mock_service):
    app = FastAPI()
    app.include_router(auth_router)

    app.dependency_overrides[get_auth_service] = lambda: mock_service
    return app


def test_login_success():
    app = create_test_app(MockAuthServiceSuccess())
    client = TestClient(app)

    response = client.post(
        "/login",
        json={
            "login": "karina",
            "password": "123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Login successful"}
    assert "access_token" in response.cookies
    assert response.cookies["access_token"] == "test_jwt_token"


def test_login_invalid_credentials():
    app = create_test_app(MockAuthServiceInvalidCredentials())
    client = TestClient(app)

    response = client.post(
        "/login",
        json={
            "login": "karina",
            "password": "wrong",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid login or password"


def test_login_blocked_account():
    app = create_test_app(MockAuthServiceBlocked())
    client = TestClient(app)

    response = client.post(
        "/login",
        json={
            "login": "karina",
            "password": "123",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is blocked"