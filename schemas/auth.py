from pydantic import BaseModel

class LoginRequest(BaseModel):
    login: str
    password: str


class TokenPayload(BaseModel):
    sub: int
    login: str