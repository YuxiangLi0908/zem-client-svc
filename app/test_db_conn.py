import os
import psycopg2

conn = psycopg2.connect(
    user=os.environ.get("dbuser"),
    password=os.environ.get("dbpass"),
    host=os.environ.get("dbhost"),
    port=int(os.environ.get("dbport")),
    database=os.environ.get("dbname"),
)