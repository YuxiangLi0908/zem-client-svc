from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.data_models.db.base import Base
from app.data_models.db.container import Container
from app.data_models.db.shipment import Shipment


class PackingList(Base):
    __tablename__ = "warehouse_packinglist"

    id = Column(Integer, primary_key=True, index=True)
    container_number_id = Column(
        Integer, ForeignKey("warehouse_container.id"), nullable=True
    )
    shipment_batch_number_id = Column(
        Integer, ForeignKey("warehouse_shipment.id"), nullable=True
    )
    # quote_id_id = Column(Integer, ForeignKey("warehouse_quote.id"), nullable=True)

    product_name = Column(String(255), nullable=True)
    delivery_method = Column(String(255), nullable=True)
    delivery_type = Column(String(255), nullable=True)
    shipping_mark = Column(String(400), nullable=True)
    fba_id = Column(String(400), nullable=True)
    destination = Column(String(255), nullable=True)
    address = Column(String(2000), nullable=True)
    zipcode = Column(String(20), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_method = Column(String(400), nullable=True)
    ref_id = Column(String(400), nullable=True)
    pcs = Column(Integer, nullable=True)
    unit_weight_lbs = Column(Float, nullable=True)
    total_weight_lbs = Column(Float, nullable=True)
    total_weight_kg = Column(Float, nullable=True)
    cbm = Column(Float, nullable=True)
    n_pallet = Column(Integer, nullable=True)
    PO_ID = Column(String(20), nullable=True)
    note = Column(String(2000), nullable=True)

    # Relationships
    container = relationship("Container", backref="packing_list")
    shipment = relationship("Shipment", backref="packing_list")
    # quote = relationship("Quote", back_populates="packing_lists")
