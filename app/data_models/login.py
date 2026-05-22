from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserAuth(BaseModel):
    user: str
    access_token: str
    user_type: str = "customer"  # customer 或 staff
