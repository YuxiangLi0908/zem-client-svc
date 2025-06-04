from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)

from app.data_models.db.base import Base


class Retrieval(Base):
    __tablename__ = "warehouse_retrieval"

    id = Column(Integer, primary_key=True, index=True)
    retrieval_id = Column(String(255), nullable=True)
    shipping_order_number = Column(String(255), nullable=True)
    master_bill_of_lading = Column(String(255), nullable=True)
    retrive_by_zem = Column(Boolean, default=True)
    retrieval_carrier = Column(String(100), nullable=True)
    origin_port = Column(String(255), nullable=True)
    destination_port = Column(String(255), nullable=True)
    shipping_line = Column(String(255), nullable=True)
    retrieval_destination_precise = Column(String(200), nullable=True)
    assigned_by_appt = Column(Boolean, default=False)
    retrieval_destination_area = Column(String(20), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    target_retrieval_timestamp = Column(DateTime, nullable=True)
    target_retrieval_timestamp_lower = Column(DateTime, nullable=True)
    actual_retrieval_timestamp = Column(DateTime, nullable=True)
    trucking_fee = Column(Float, nullable=True)
    chassis_fee = Column(Float, nullable=True)
    is_trucking_fee_paid = Column(Boolean, default=False)
    is_chassis_fee_paid = Column(Boolean, default=False)
    trucking_fee_paid_at = Column(Float, nullable=True)
    chassis_fee_paid_at = Column(Float, nullable=True)
    note = Column(Text, nullable=True)
    arrive_at_destination = Column(Boolean, default=False)
    arrive_at = Column(DateTime, nullable=True)
    empty_returned = Column(Boolean, default=False)
    empty_returned_at = Column(DateTime, nullable=True)
    temp_t49_lfd = Column(Date, nullable=True)
    temp_t49_available_for_pickup = Column(Boolean, default=False)
    temp_t49_pod_arrive_at = Column(DateTime, nullable=True)
    temp_t49_pod_discharge_at = Column(DateTime, nullable=True)
    temp_t49_hold_status = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_retrieval_id", "retrieval_id"),
        Index("ix_target_retrieval_timestamp", "target_retrieval_timestamp"),
    )
