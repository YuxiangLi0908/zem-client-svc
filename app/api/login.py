import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.data_models.db.user import Customer
from app.data_models.login import LoginRequest, UserAuth
from app.services.config import app_config
from app.services.db_session import db_session

router = APIRouter()


@router.post("/login", response_model=UserAuth, name="login")
async def login(request: LoginRequest, db: Session = Depends(db_session.get_db)):
    db_user = db.query(Customer).filter(Customer.username == request.username).first()
    pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"], deprecated="auto")
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    elif not pwd_context.verify(request.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    user_type = "staff" if db_user.username == "superuser" else "customer"
    token = jwt.encode(
        {
            "user_name": db_user.username,
            "zem_name": db_user.zem_name,
            "user_type": user_type,
        },
        app_config.SECRET_KEY,
        algorithm=app_config.JWT_ALGO,
    )
    return {"user": db_user.zem_name, "access_token": token, "user_type": user_type}
