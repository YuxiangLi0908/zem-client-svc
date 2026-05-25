from sqlalchemy import Boolean, Column, Float, Integer, String, Text

from app.data_models.db.base import Base


class Customer(Base):
    __tablename__ = "warehouse_customer"

    id = Column(Integer, primary_key=True, index=True)
    zem_name = Column(String(200), unique=True, index=True)
    full_name = Column(String(200), nullable=True)
    accounting_name = Column(String(200), nullable=True)
    zem_code = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(30), nullable=True)
    note = Column(String(500), nullable=True)
    address = Column(String(500), nullable=True)
    username = Column(String(150), unique=True, nullable=True)
    password = Column(String(255), nullable=True)
    balance = Column(Float, nullable=True, default=0.0)


class AuthUser(Base):
    __tablename__ = "auth_user"

    id = Column(Integer, primary_key=True, index=True)
    password = Column(String(128), nullable=False)
    last_login = Column(String, nullable=True)
    is_superuser = Column(Boolean, default=False)
    username = Column(String(150), unique=True, nullable=False)
    first_name = Column(String(150), default="")
    last_name = Column(String(150), default="")
    email = Column(String(254), default="")
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    date_joined = Column(String, nullable=False)
