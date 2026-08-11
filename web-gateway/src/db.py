import os
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
from psycopg2 import errors as pg_errors

pool = None
pool_error = None


def _init_pool():
    global pool, pool_error
    if pool is not None:
        return pool

    try:
        pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.environ.get('DB_HOST', 'postgres'),
            port=os.environ.get('DB_PORT', '5432'),
            dbname=os.environ.get('DB_NAME', 'app_db'),
            user=os.environ.get('DB_USER', 'app_user'),
            password=os.environ.get('DB_PASSWORD')
        )
    except Exception as exc:
        pool_error = exc
        pool = None

    return pool


def get_conn():
    conn_pool = _init_pool()
    if conn_pool is None:
        raise RuntimeError("Database pool is unavailable") from pool_error
    return conn_pool.getconn()


def put_conn(conn):
    if pool is not None:
        pool.putconn(conn)


def close_pool():
    global pool
    if pool is not None:
        pool.closeall()
        pool = None


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


def get_user_by_id(user_id: int):
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, username, password_hash, role, email, display_name, created_at FROM users WHERE id = %s",
            (user_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        put_conn(conn)


def get_user_profile_by_id(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        return None
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "email": user["email"],
        "display_name": user["display_name"],
        "created_at": user["created_at"],
    }


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


def update_user_profile(user_id: int, email, display_name):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET email = %s, display_name = %s WHERE id = %s",
            (email, display_name, user_id)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        put_conn(conn)


def update_user_password(user_id: int, password_hash: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (password_hash, user_id)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        put_conn(conn)


def get_all_users():
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, username, role, email, display_name, created_at FROM users ORDER BY id"
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        cur.close()
        put_conn(conn)


def update_user_role(user_id: int, role: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        put_conn(conn)


def create_activity_log(user_id: int, action: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO activity_log (user_id, action) VALUES (%s, %s)",
            (user_id, action)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        put_conn(conn)


def get_user_activity_logs(user_id: int):
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT action, created_at FROM activity_log WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
            (user_id,)
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        cur.close()
        put_conn(conn)