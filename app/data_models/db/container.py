from sqlalchemy import Boolean, Column, Float, Integer, String

from app.data_models.db.base import Base


class Container(Base):
    __tablename__ = "warehouse_container"

    id = Column(Integer, primary_key=True, index=True)
    container_number = Column(String(255), nullable=True)
    container_type = Column(String(255), nullable=True)
    weight_lbs = Column(Float, nullable=True)
    is_special_container = Column(Boolean, nullable=True, default=False)
    note = Column(String(100), nullable=True)
