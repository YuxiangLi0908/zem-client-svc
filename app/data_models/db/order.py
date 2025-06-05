from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.data_models.db.base import Base
from app.data_models.db.container import Container
from app.data_models.db.offload import Offload
from app.data_models.db.retrieval import Retrieval
from app.data_models.db.vessel import Vessel
from app.data_models.db.warehouse import Warehouse


class Order(Base):
    __tablename__ = "warehouse_order"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(255), nullable=True)
    customer_name_id = Column(
        Integer, ForeignKey("warehouse_customer.id"), nullable=True
    )
    container_number_id = Column(
        Integer, ForeignKey("warehouse_container.id"), nullable=True
    )
    warehouse_id = Column(
        Integer, ForeignKey("warehouse_zemwarehouse.id"), nullable=True
    )
    vessel_id_id = Column(Integer, ForeignKey("warehouse_vessel.id"), nullable=True)
    retrieval_id_id = Column(
        Integer, ForeignKey("warehouse_retrieval.id"), nullable=True
    )
    offload_id_id = Column(Integer, ForeignKey("warehouse_offload.id"), nullable=True)
    shipment_id_id = Column(Integer, ForeignKey("warehouse_shipment.id"), nullable=True)
    invoice_id_id = Column(Integer, ForeignKey("warehouse_invoice.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    eta = Column(Date, nullable=True)
    order_type = Column(String(255), nullable=True)
    customer_do_link = Column(String(2000), nullable=True)
    do_sent = Column(Boolean, default=False)
    add_to_t49 = Column(Boolean, default=False)
    packing_list_updloaded = Column(Boolean, default=False)
    cancel_notification = Column(Boolean, default=False)
    cancel_time = Column(Date, nullable=True)
    invoice_status = Column(String(255), nullable=True)
    invoice_reject = Column(Boolean, default=False)
    invoice_reject_reason = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", backref="order")
    container = relationship("Container", backref="order")
    warehouse = relationship("Warehouse", backref="order")
    vessel = relationship("Vessel", backref="order")
    retrieval = relationship("Retrieval", backref="order")
    offload = relationship("Offload", backref="order")
    # shipment = relationship("Shipment", back_populates="order")

    __table_args__ = (
        Index("ix_order_order_id", "order_id"),
        Index("ix_order_eta", "eta"),
        Index("ix_order_created_at", "created_at"),
    )
    