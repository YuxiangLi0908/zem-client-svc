from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String

from app.data_models.db.base import Base


class Offload(Base):
    __tablename__ = "warehouse_offload"

    id = Column(Integer, primary_key=True, index=True)
    offload_id = Column(String(255), nullable=True)
    offload_required = Column(Boolean, default=True)
    offload_at = Column(DateTime, nullable=True)
    total_pallet = Column(Integer, nullable=True)
    devanning_company = Column(String(100), nullable=True)
    devanning_fee = Column(Float, nullable=True)
    devanning_fee_paid_at = Column(Date, nullable=True)
    is_devanning_fee_paid = Column(String(100), nullable=True)
