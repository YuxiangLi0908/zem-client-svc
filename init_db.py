from sqlalchemy import create_engine

from app.data_models.db import Base
from app.services.db_session import db_session


def create_tables():
    engine = create_engine(db_session.database_url)
    Base.metadata.create_all(bind=engine)
    print("数据库表创建成功！")
    print("创建的表:")
    print("  - quotation_master")
    print("  - fee_detail")


if __name__ == "__main__":
    create_tables()
