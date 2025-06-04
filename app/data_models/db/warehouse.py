from sqlalchemy import Column, Integer, String

from app.data_models.db.base import Base


class Warehouse(Base):
    __tablename__ = "warehouse_zemwarehouse"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200))
    address = Column(String(200), nullable=True)
