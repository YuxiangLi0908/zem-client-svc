import os
import psycopg2

conn = psycopg2.connect(
    user=os.environ.get("DBUSER"),
    password=os.environ.get("DBPASS"),
    host=os.environ.get("DBHOST"),
    port=int(os.environ.get("DBPORT")),
    database=os.environ.get("DBNAME"),
)