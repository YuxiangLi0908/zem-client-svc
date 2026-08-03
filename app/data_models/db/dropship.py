from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.data_models.db.base import Base


class DropshipShipment(Base):
    __tablename__ = "warehouse_dropshipshipment"

    id = Column(Integer, primary_key=True, index=True)
    shipment_batch_number = Column(String(255), unique=True, nullable=True)
    status = Column(String(20), default="pending")
    warehouse_id = Column(Integer, ForeignKey("warehouse_zemwarehouse.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    pickup_time = Column(Date, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    arrived_at = Column(DateTime, nullable=True)
    total_pcs = Column(Integer, default=0)
    pod_link = Column(String(2000), nullable=True)
    pod_uploaded_at = Column(DateTime, nullable=True)
    shipping_address = Column(Text, nullable=True)
    contact_person = Column(String(100), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    note = Column(Text, nullable=True)
    operator = Column(String(100), nullable=True)

    details = relationship("DropshipShipmentDetail", back_populates="shipment")


class DropshipCargo(Base):
    __tablename__ = "warehouse_dropshipcargo"

    id = Column(Integer, primary_key=True, index=True)
    shipping_mark = Column(String(255), nullable=True, index=True)
    model = Column(String(255), nullable=True)
    product_name = Column(String(255), nullable=True)
    container_id = Column(Integer, ForeignKey("warehouse_container.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("warehouse_order.id"), nullable=True)
    warehouse_id = Column(Integer, ForeignKey("warehouse_zemwarehouse.id"), nullable=True)
    pcs = Column(Integer, default=0)
    pallets = Column(Integer, default=0)
    unit_weight_lbs = Column(Numeric, nullable=True)
    total_weight_lbs = Column(Numeric, nullable=True)
    total_weight_kg = Column(Numeric, nullable=True)
    cbm = Column(Numeric, nullable=True)
    long = Column(Numeric(10, 2), nullable=True)
    width = Column(Numeric(10, 2), nullable=True)
    height = Column(Numeric(10, 2), nullable=True)
    PO_ID = Column(String(200), nullable=True)
    shipped_quantity = Column(Integer, default=0)
    returned_quantity = Column(Integer, default=0)
    delivery_type = Column(String(20), default="一件代发")
    delivery_method = Column(String(20), default="pickup")
    address = Column(Text, nullable=True)
    status = Column(String(20), default="not_in_stock")
    note = Column(Text, nullable=True)


class DropshipShipmentDetail(Base):
    __tablename__ = "warehouse_dropshipshipmentdetail"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("warehouse_dropshipshipment.id"), nullable=True)
    cargo_id = Column(Integer, ForeignKey("warehouse_dropshipcargo.id"), nullable=True)
    pcs = Column(Integer, nullable=True)
    returned_pcs = Column(Integer, default=0)
    pallets = Column(Integer, default=0)
    note = Column(Text, nullable=True)

    shipment = relationship("DropshipShipment", back_populates="details")
    cargo = relationship("DropshipCargo")


class DropshipInventory(Base):
    __tablename__ = "warehouse_dropshipinventory"

    id = Column(Integer, primary_key=True, index=True)
    cargo_id = Column(Integer, ForeignKey("warehouse_dropshipcargo.id"), nullable=True)
    transaction_type = Column(String(20), nullable=True)
    pcs_change = Column(Integer, nullable=True)
    after_pcs = Column(Integer, nullable=True)
    shipment_detail_id = Column(Integer, ForeignKey("warehouse_dropshipshipmentdetail.id"), nullable=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    operator = Column(String(100), nullable=True)
    note = Column(Text, nullable=True)
    is_verify = Column(Boolean, default=False)
    verfiy_pcs_change = Column(Integer, nullable=True)
    verify_pcs = Column(Integer, nullable=True)
