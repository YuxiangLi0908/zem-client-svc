from sqlalchemy import Boolean, Column, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.data_models.db.base import Base
from app.data_models.db.container import Container
from app.data_models.db.shipment import Shipment


class Pallet(Base):
    __tablename__ = "warehouse_pallet"

    id = Column(Integer, primary_key=True, index=True)
    packing_list_id = Column(Integer, ForeignKey("warehouse_packinglist.id"), nullable=True)
    container_number_id = Column(Integer, ForeignKey("warehouse_container.id"), nullable=True)
    shipment_batch_number_id = Column(Integer, ForeignKey("warehouse_shipment.id"), nullable=True)
    master_shipment_batch_number_id = Column(Integer, ForeignKey("warehouse_shipment.id"), nullable=True)
    transfer_batch_number_id = Column(Integer, nullable=True)
    invoice_delivery_id = Column(Integer, nullable=True)

    destination = Column(String(255), nullable=True)
    delivery_window_start = Column(String, nullable=True)
    delivery_window_end = Column(String, nullable=True)
    is_dropped_pallet = Column(Boolean, nullable=True, default=False)
    address = Column(String(2000), nullable=True)
    zipcode = Column(String(20), nullable=True)
    delivery_method = Column(String(255), nullable=True)
    delivery_type = Column(String(255), nullable=True)
    pallet_id = Column(String(255), nullable=True)
    PO_ID = Column(String(20), nullable=True)
    slot = Column(String(20), nullable=True)
    shipping_mark = Column(String(4000), nullable=True)
    fba_id = Column(String(4000), nullable=True)
    ref_id = Column(String(4000), nullable=True)
    pcs = Column(Integer, nullable=True)
    sequence_number = Column(String(2000), nullable=True)
    length = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    cbm = Column(Float, nullable=True)
    weight_lbs = Column(Float, nullable=True)
    abnormal_palletization = Column(Boolean, default=False, nullable=True)
    po_expired = Column(Boolean, default=False, nullable=True)
    note = Column(String(8000), nullable=True)
    note_sp = Column(String(2000), nullable=True)
    priority = Column(String(20), nullable=True)
    location = Column(String(100), nullable=True)
    contact_name = Column(String(255), nullable=True)
    ltl_supplier = Column(String(100), nullable=True)
    carrier_company = Column(String(200), nullable=True)
    ltl_bol_num = Column(String(200), nullable=True)
    ltl_pro_num = Column(String(200), nullable=True)
    PickupAddr = Column(String(200), nullable=True)
    est_pickup_time = Column(String, nullable=True)
    ltl_cost = Column(Float, nullable=True)
    ltl_quote = Column(Float, nullable=True)
    ltl_unit_quote = Column(Float, nullable=True)
    ltl_follow_status = Column(String(200), nullable=True)
    ltl_release_command = Column(String(400), nullable=True)
    ltl_cost_note = Column(String(400), nullable=True)
    ltl_quote_note = Column(String(400), nullable=True)
    ltl_contact_method = Column(String(400), nullable=True)
    del_qty = Column(Float, nullable=True)
    ltl_plt_size_note = Column(String(1000), nullable=True)
    ltl_correlation_id = Column(String(400), nullable=True)
    shipment_note = Column(String(1000), nullable=True)
    ltl_address = Column(String(1000), nullable=True)
    ltl_city = Column(String(100), nullable=True)
    ltl_state = Column(String(100), nullable=True)
    ltl_zipcode = Column(String(100), nullable=True)
    ltl_address_type = Column(String(100), nullable=True)

    container = relationship("Container", backref="pallet")
    shipment = relationship(
        "Shipment",
        foreign_keys=[master_shipment_batch_number_id],
        backref="pallets_master",
    )
    exceptions = relationship("PalletException", backref="pallet")

    __table_args__ = (Index("ix_pallet_PO_ID", "PO_ID"),)
