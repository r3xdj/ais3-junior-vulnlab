import os
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
from psycopg2 import errors as pg_errors

pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=os.environ.get('DB_HOST', 'postgres'),      # docker-compose service name
    port=os.environ.get('DB_PORT', '5432'),
    dbname=os.environ.get('DB_NAME', 'app_db'),
    user=os.environ.get('DB_USER', 'app_user'),
    password=os.environ.get('DB_PASSWORD')            # 必須從環境變數讀,不 hardcode
)


def get_conn():
    return pool.getconn()

def put_conn(conn):
    pool.putconn(conn)

def close_pool():
    pool.closeall()

def get_user_by_username(username: str):
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, username, password_hash, role, created_at FROM users WHERE username = %s",
            (username,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        put_conn(conn)


def create_user(username: str, password_hash: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
            (username, password_hash)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return user_id
    except pg_errors.UniqueViolation:
        conn.rollback()
        raise
    finally:
        cur.close()
        put_conn(conn)