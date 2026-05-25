from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.data_models.db.base import Base
from app.data_models.db.container import Container
from app.data_models.db.shipment import Shipment


class PackingList(Base):
    __tablename__ = "warehouse_packinglist"

    id = Column(Integer, primary_key=True, index=True)
    container_number_id = Column(Integer, ForeignKey("warehouse_container.id"), nullable=True)
    shipment_batch_number_id = Column(Integer, ForeignKey("warehouse_shipment.id"), nullable=True)
    master_shipment_batch_number_id = Column(Integer, ForeignKey("warehouse_shipment.id"), nullable=True)
    quote_id_id = Column(Integer, nullable=True)

    product_name = Column(String(255), nullable=True)
    delivery_method = Column(String(255), nullable=True)
    delivery_type = Column(String(255), nullable=True)
    shipping_mark = Column(String(2000), nullable=True)
    fba_id = Column(String(4000), nullable=True)
    destination = Column(String(4000), nullable=True)
    address = Column(String(2000), nullable=True)
    zipcode = Column(String(200), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_method = Column(String(400), nullable=True)
    ref_id = Column(String(2000), nullable=True)
    pcs = Column(Integer, nullable=True)
    delivery_window_start = Column(String, nullable=True)
    delivery_window_end = Column(String, nullable=True)
    unit_weight_lbs = Column(Float, nullable=True)
    total_weight_lbs = Column(Float, nullable=True)
    total_weight_kg = Column(Float, nullable=True)
    cbm = Column(Float, nullable=True)
    n_pallet = Column(Integer, nullable=True)
    PO_ID = Column(String(200), nullable=True)
    note = Column(String(6000), nullable=True)
    office_note = Column(String(6000), nullable=True)
    note_sp = Column(String(2000), nullable=True)
    express_number = Column(String, nullable=True)
    long = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    ltl_verify = Column(Boolean, nullable=True, default=False)
    ltl_supplier = Column(String(100), nullable=True)
    carrier_company = Column(String(200), nullable=True)
    ltl_bol_num = Column(String(200), nullable=True)
    ltl_pro_num = Column(String(200), nullable=True)
    PickupAddr = Column(String(200), nullable=True)
    est_pickup_time = Column(String, nullable=True)
    ltl_follow_status = Column(String(400), nullable=True)
    ltl_release_command = Column(String(400), nullable=True)
    ltl_contact_method = Column(String(400), nullable=True)
    ltl_correlation_id = Column(String(400), nullable=True)
    shipment_note = Column(String(1000), nullable=True)
    ltl_address = Column(String(1000), nullable=True)
    ltl_city = Column(String(100), nullable=True)
    ltl_state = Column(String(100), nullable=True)
    ltl_zipcode = Column(String(100), nullable=True)
    ltl_address_type = Column(String(100), nullable=True)

    container = relationship("Container", backref="packing_list")
    shipment = relationship("Shipment", backref="packing_list")
