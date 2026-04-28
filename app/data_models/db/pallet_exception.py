# app/data_models/db/pallet_exception.py

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.data_models.db.base import Base
from app.data_models.db.pallet import Pallet


class PalletException(Base):
    __tablename__ = "warehouse_palletexception"

    id = Column(Integer, primary_key=True, index=True)
    pallet_id = Column(Integer, ForeignKey("warehouse_pallet.id"), nullable=False)
    exception_type = Column(String(50), nullable=False)
    exception_reason = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships

    __table_args__ = (
        Index("ix_pallet_exception_pallet_id", "pallet_id"),
        Index("ix_pallet_exception_exception_type", "exception_type"),
    )
