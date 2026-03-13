from fastapi import APIRouter, Depends, HTTPException, Response, status

from dependencies.auth import get_auth_service
from schemas.auth import LoginRequest
from services.auth import AuthService
from errors.auth_exceptions import InvalidCredentialsError, AccountBlockedError

auth_router = APIRouter()


@auth_router.post(
    "/login",
    status_code=status.HTTP_200_OK,
)
async def login(
    dto: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    try:
        account = await auth_service.login(dto.login, dto.password)
        access_token = auth_service.create_access_token(account)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False, # для локальной разработки
            samesite="lax",
            max_age=60 * 60,
        )
        return {"message": "Login successful"}
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login or password",
        )
    except AccountBlockedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
        )