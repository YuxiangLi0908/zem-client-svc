import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.data_models.db.user import Customer, AuthUser
from app.services.config import app_config
from app.services.db_session import db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(db_session.get_db),
) -> Customer | AuthUser:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, app_config.SECRET_KEY, algorithms=[app_config.JWT_ALGO]
        )
        username: str = payload.get("user_name")
        if username is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    user_type: str = payload.get("user_type")

    if user_type == "staff":
        auth_user = db.query(AuthUser).filter(AuthUser.username == username).first()
        if auth_user:
            return auth_user
        customer = db.query(Customer).filter(Customer.username == username).first()
        if customer:
            return customer
        raise credentials_exception

    if user_type == "customer":
        customer = db.query(Customer).filter(Customer.username == username).first()
        if customer:
            return customer
        raise credentials_exception

    customer = db.query(Customer).filter(Customer.username == username).first()
    if customer:
        return customer

    auth_user = db.query(AuthUser).filter(AuthUser.username == username).first()
    if auth_user:
        return auth_user

    raise credentials_exception
