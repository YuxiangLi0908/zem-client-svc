from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship

from app.data_models.db.base import Base
from app.data_models.db.container import Container
from app.data_models.db.user import Customer


class Invoicev2(Base):
    __tablename__ = "warehouse_invoicev2"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(200), nullable=True)
    invoice_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    invoice_link = Column(String(2000), nullable=True)
    customer_id = Column(Integer, ForeignKey("warehouse_customer.id"), nullable=True)
    container_number_id = Column(Integer, ForeignKey("warehouse_container.id"), nullable=True)
    is_master_bill = Column(Boolean, default=False)

    receivable_total_amount = Column(Float, nullable=True)
    receivable_preport_amount = Column(Float, nullable=True)
    receivable_wh_public_amount = Column(Float, nullable=True)
    receivable_wh_other_amount = Column(Float, nullable=True)
    receivable_delivery_public_amount = Column(Float, nullable=True)
    receivable_delivery_other_amount = Column(Float, nullable=True)
    receivable_direct_amount = Column(Float, nullable=True)

    payout_total_amount = Column(Float, nullable=True)
    receivable_is_locked = Column(Boolean, default=False)
    is_invoice_delivered = Column(Boolean, default=False)
    received_amount = Column(Float, nullable=True)
    remain_offset = Column(Float, nullable=True)

    statement_id_id = Column(Integer, nullable=True)

    payable_total_amount = Column(Float, nullable=True)
    payable_preport_amount = Column(Float, nullable=True)
    payable_warehouse_amount = Column(Float, nullable=True)
    payable_delivery_amount = Column(Float, nullable=True)
    payable_delivery_cost = Column(Numeric(15, 4), nullable=True)
    payable_delivery_refund = Column(Numeric(15, 4), nullable=True)
    payable_delivery_transfer = Column(Numeric(15, 4), nullable=True)

    container = relationship("Container", backref="invoicesv2")
    customer = relationship("Customer", backref="invoicesv2")


class InvoiceStatusv2(Base):
    __tablename__ = "warehouse_invoicestatusv2"

    id = Column(Integer, primary_key=True, index=True)
    container_number_id = Column(Integer, ForeignKey("warehouse_container.id"), nullable=True)
    invoice_id = Column(Integer, ForeignKey("warehouse_invoicev2.id"), nullable=True)
    invoice_type = Column(String(20), nullable=True)
    preport_status = Column(String(20), default="unstarted")
    warehouse_public_status = Column(String(20), default="unstarted")
    warehouse_other_status = Column(String(20), default="unstarted")
    delivery_public_status = Column(String(20), default="unstarted")
    delivery_other_status = Column(String(20), default="unstarted")
    finance_status = Column(String(20), default="unstarted")
    preport_reason = Column(Text, nullable=True)
    warehouse_public_reason = Column(Text, nullable=True)
    warehouse_self_reason = Column(Text, nullable=True)
    delivery_public_reason = Column(Text, nullable=True)
    delivery_other_reason = Column(Text, nullable=True)
    payable_status = Column(Text, nullable=True)
    payable_date = Column(DateTime, nullable=True)

    container_number = relationship("Container", backref="invoice_statusesv2")
    invoice = relationship("Invoicev2", backref="statuses")


class InvoiceItemv2(Base):
    __tablename__ = "warehouse_invoiceitemv2"

    id = Column(Integer, primary_key=True, index=True)
    container_number_id = Column(Integer, ForeignKey("warehouse_container.id"), nullable=True)
    invoice_number_id = Column(Integer, ForeignKey("warehouse_invoicev2.id"), nullable=True)
    invoice_type = Column(String(20), nullable=True)
    item_category = Column(String(30), nullable=True)
    cbm = Column(Float, nullable=True)
    cbm_ratio = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    description = Column(String(1000), nullable=True)
    qty = Column(Float, nullable=True)
    rate = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)
    PO_ID = Column(String(20), nullable=True)
    delivery_type = Column(String(50), nullable=True)
    warehouse_code = Column(String(200), nullable=True)
    shipping_marks = Column(Text, nullable=True)
    region = Column(String(200), nullable=True)
    regionPrice = Column(Float, nullable=True)
    surcharges = Column(Float, nullable=True)
    note = Column(String(2000), nullable=True)
    registered_user = Column(String(2000), nullable=True)
    carrier = Column(String(255), nullable=True)
    write_off_time = Column(DateTime, nullable=True)
    write_off_amount = Column(Numeric(12, 2), nullable=True)

    container_number = relationship("Container", backref="invoice_itemv2")
    invoice = relationship("Invoicev2", backref="items")
