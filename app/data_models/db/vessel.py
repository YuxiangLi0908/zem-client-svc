from sqlalchemy import Column, DateTime, Integer, String

from app.data_models.db.base import Base


class Vessel(Base):
    __tablename__ = "warehouse_vessel"

    id = Column(Integer, primary_key=True, index=True)
    vessel_id = Column(String(255), nullable=True, index=True)
    master_bill_of_lading = Column(String(255), nullable=True, index=True)
    origin_port = Column(String(255), nullable=True)
    destination_port = Column(String(255), nullable=True)
    shipping_line = Column(String(255), nullable=True)
    vessel = Column(String(100), nullable=True, index=True)
    voyage = Column(String(100), nullable=True, index=True)
    vessel_etd = Column(DateTime, nullable=True)
    vessel_eta = Column(DateTime, nullable=True)
