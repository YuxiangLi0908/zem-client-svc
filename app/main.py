import os
import pandas as pd

from sqlalchemy import text
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.test_db_conn import conn


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(GZipMiddleware)

@app.get("/")
def read_root():
    return {"message": "Hello, Azure Container Registry and Container Apps with Github CI/CD!"}

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
    df = pd.read_sql("SELECT * FROM public.warehouse_vessel WHERE vessel_eta > '2025-01-02'", con=conn)
    return {"tables": df.to_dict()}