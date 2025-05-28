import os

import pandas as pd
import psycopg2
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.api.router import api_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(GZipMiddleware)
app.include_router(api_router)


def get_connection():
    if os.environ.get("ENV", "local") == "production":
        conn = psycopg2.connect(
            user=os.environ.get("DBUSER"),
            password=os.environ.get("DBPASS"),
            host=os.environ.get("DBHOST"),
            port=int(os.environ.get("DBPORT")),
            database=os.environ.get("DBNAME"),
        )
    else:
        conn = psycopg2.connect(
            user="postgres",
            password=os.environ.get("POSTGRESQL_PWD"),
            host="127.0.0.1",
            port="5432",
            database="zem",
        )
    return conn


@app.get("/")
def read_root():
    return {"message": "Hello, Azure Container Registry and Container Apps!"}


@app.get("/dbconn")
def read_root():
    return {
        "DBNAME": os.environ.get("DBNAME", ""),
        "DBHOST": os.environ.get("DBHOST", ""),
        "DBPORT": os.environ.get("DBPORT", ""),
        "DBUSER": os.environ.get("DBUSER", ""),
    }


@app.get("/dbtest")
def read_db():
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM public.warehouse_vessel WHERE vessel_eta > '2025-01-02'",
        con=conn,
    )
    return {"tables": df.to_dict()}


@app.get("/api/data")
async def get_data():
    # Simulate fetching data
    return {"message": "Hello from FastAPI!"}


DATABASE_URL = "postgresql://postgres:Dlmm04121313!@127.0.0.1/zem"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.data_models.user import User


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/users")
def read_users(db: Session = Depends(get_db)):
    return db.query(User).all()


pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


@app.post("/test_login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.zem_name == username).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    elif not verify_password(password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return {"user": db_user}
