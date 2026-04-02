from sqlalchemy import Column, Integer, String, Date, Boolean

from app.data_models.db.base import Base


class QuotationMaster(Base):
    __tablename__ = "warehouse_quotationMaster"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(String(200), nullable=True)
    upload_date = Column(Date, nullable=True)
    version = Column(String(2000), nullable=True)
    quote_type = Column(String(20), nullable=False, default="receivable")
    filename = Column(String(2000), nullable=True)
    is_user_exclusive = Column(Boolean, nullable=False, default=False)
    exclusive_user = Column(String(2000), nullable=True)
    effective_date = Column(Date, nullable=True)
