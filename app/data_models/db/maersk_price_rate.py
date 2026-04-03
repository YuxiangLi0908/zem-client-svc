from sqlalchemy import Column, Integer, String, Date, Float, Boolean
from app.data_models.db.base import Base


class MaerskPriceRate(Base):
    __tablename__ = "warehouse_maerskpricerate"

    id = Column(Integer, primary_key=True, index=True)
    rate_id = Column(String(200), nullable=True)
    is_user_exclusive = Column(Boolean, default=False)
    exclusive_user = Column(String(2000), nullable=True)
    effective_date = Column(Date, nullable=True)
    increase_percentage = Column(Float, nullable=False)
