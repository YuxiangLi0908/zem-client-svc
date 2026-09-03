from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, func

from app.data_models.db.base import Base


class MultiCarrierQuoteHistory(Base):
    __tablename__ = "warehouse_multi_carrier_quote_history"

    id = Column(Integer, primary_key=True, index=True)
    origin_warehouse = Column(String(100), nullable=False, index=True)
    destination_warehouse = Column(String(100), nullable=False, index=True)
    pickup_date = Column(Date, nullable=False, index=True)
    quote_type = Column(String(20), nullable=False, index=True)
    ftl_car_type = Column(String(100), nullable=False, default="")
    freight_class = Column(String(20), nullable=False, default="")
    declared_value = Column(Numeric(12, 2), nullable=False)
    pallet_items = Column(JSON, nullable=False, default=list)
    maersk_quotes = Column(JSON, nullable=False, default=dict)
    kakas_quotes = Column(JSON, nullable=False, default=dict)
    abf_quotes = Column(JSON, nullable=False, default=dict)
    operator_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
