import os

import psycopg2


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
        user='postgres',
        password=os.environ.get("POSTGRESQL_PWD"),
        host='127.0.0.1',
        port='5432',
        database='zem',
    )