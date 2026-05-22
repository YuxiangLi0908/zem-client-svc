from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.data_models.db.base import Base


class Customer(Base):
    """
    客户用户表
    对应 Django 模型中的 warehouse_customer 表
    """
    __tablename__ = "warehouse_customer"

    id = Column(Integer, primary_key=True, index=True)
    zem_name = Column(String, unique=True, index=True)
    full_name = Column(String)
    zem_code = Column(String)
    email = Column(String)
    note = Column(String)
    phone = Column(String)
    accounting_name = Column(String)
    address = Column(String)
    username = Column(String, unique=True)
    password = Column(String)


class AuthUser(Base):
    """
    员工用户表（Django 内置 auth_user 表）
    用于员工登录验证
    """
    __tablename__ = "auth_user"

    id = Column(Integer, primary_key=True, index=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime, nullable=True)
    is_superuser = Column(Boolean, default=False)
    username = Column(String(150), unique=True, nullable=False)
    first_name = Column(String(150), default="")
    last_name = Column(String(150), default="")
    email = Column(String(254), default="")
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    date_joined = Column(DateTime, nullable=False)


# 为了保持兼容性，保留 User 别名指向 Customer
User = Customer
