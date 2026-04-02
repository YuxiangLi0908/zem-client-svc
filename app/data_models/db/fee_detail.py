from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.data_models.db.quotation_master import QuotationMaster
from app.data_models.db.base import Base


class FeeDetail(Base):
    __tablename__ = "warehouse_feeDetail"

    id = Column(Integer, primary_key=True, index=True)
    fee_detail_id = Column(String(200), nullable=True)
    quotation_id_id = Column(Integer, ForeignKey("warehouse_quotationMaster.id"), nullable=False, index=True)
    fee_type = Column(String(255), nullable=True)
    warehouse = Column(String(20), nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    niche_warehouse = Column(String(2000), nullable=True)

    # Relationships
    quotation_master = relationship("QuotationMaster", backref="fee_detail")
