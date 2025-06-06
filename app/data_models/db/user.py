from sqlalchemy import Column, Integer, String

from app.data_models.db.base import Base


class User(Base):
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
