import os
from typing import Generator

import psycopg2
from psycopg2.extensions import connection
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class DBSession:
    def __init__(self) -> None:
        if os.environ.get("ENV", "local") == "production":
            self.user = os.environ.get("DBUSER")
            self.password = os.environ.get("DBPASS")
            self.host = os.environ.get("DBHOST")
            self.port = int(os.environ.get("DBPORT"))
            self.database = os.environ.get("DBNAME")
        else:
            self.user = "postgres"
            self.password = os.environ.get("POSTGRESQL_PWD")
            self.host = "127.0.0.1"
            self.port = 5432
            self.database = "zem"
        self.database_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def get_db(self) -> Generator[Session, None, None]:
        engine = create_engine(self.database_url)
        session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    def get_connection(self) -> connection:
        conn = psycopg2.connect(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )
        return conn


db_session = DBSession()
