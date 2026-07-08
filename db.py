import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host = os.getenv("POSTGRES_HOST","localhost"),
        port = os.getenv("POSTGRES_PORT","5432"),
        dbname = os.getenv("POSTGRES_DB","blog_db"),
        user = os.getenv("POSTGRES_USER","bloguser"),
        password = os.getenv("POSTGRES_PASSWORD","blogpass")
    )

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    #-------User table ----------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
    );
    """)

    #---- Blog Table -------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS blogs(
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255)  NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPZ DEFAULT now()
    );
    """)


    conn.commit()
    cur.close()
    conn.close()
    print("Database initalized")