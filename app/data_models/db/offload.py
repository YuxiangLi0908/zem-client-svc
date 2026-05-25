from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from app.data_models.db.base import Base


class Offload(Base):
    __tablename__ = "warehouse_offload"

    id = Column(Integer, primary_key=True, index=True)
    offload_id = Column(String(255), nullable=True)
    offload_required = Column(Boolean, default=True)
    offload_at = Column(DateTime, nullable=True)
    offload_other_at = Column(DateTime, nullable=True)
    offload_other_selfdelivery_at = Column(DateTime, nullable=True)
    offload_other_selfpick_cargos_at = Column(DateTime, nullable=True)
    offload_at_container = Column(DateTime, nullable=True)
    total_pallet = Column(Integer, nullable=True)
    public_total_pallet = Column(Integer, nullable=True)
    other_total_pallet = Column(Integer, nullable=True)
    other_selfdelivery_total_pallet = Column(Integer, nullable=True)
    other_selfpick_cargos_total_pallet = Column(Integer, nullable=True)
    devanning_company = Column(String(100), nullable=True)
    devanning_fee = Column(Float, nullable=True)
    devanning_fee_paid_at = Column(DateTime, nullable=True)
    is_devanning_fee_paid = Column(String(100), nullable=True)
    warehouse_unpacked_time = Column(DateTime, nullable=True)
    warehouse_unpacking_time = Column(DateTime, nullable=True)
    arrival_location = Column(String(100), nullable=True)
    unpacking_status = Column(String(10), nullable=True, default="0")
    image_link = Column(String(2000), nullable=True)
    uploaded_at = Column(DateTime, nullable=True)
    offload_note = Column(String(2000), nullable=True)
