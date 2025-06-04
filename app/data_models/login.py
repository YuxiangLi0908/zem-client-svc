from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserAuth(BaseModel):
    user: str
    access_token: str
