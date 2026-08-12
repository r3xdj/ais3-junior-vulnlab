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

    if pool is not None:
        try:
            _ensure_certificate_schema()
        except Exception as exc:
            pool_error = exc
            pool.closeall()
            pool = None

    return pool


def _ensure_certificate_schema():
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS certificates (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                scores JSONB NOT NULL,
                average_score NUMERIC(5,2) NOT NULL,
                grade VARCHAR(5) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                file_name VARCHAR(255),
                issued_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT certificates_status_check CHECK (status IN ('pending', 'issued', 'failed'))
            )
            """
        )
        # Display Name 預設與帳號名稱相同；也補齊既有資料。
        cur.execute("UPDATE users SET display_name = username WHERE display_name IS NULL OR BTRIM(display_name) = ''")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        pool.putconn(conn)


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
            "SELECT id, username, password_hash, role, email, display_name, exam_type, created_at FROM users WHERE id = %s",
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
        "exam_type": user["exam_type"],
        "created_at": user["created_at"],
    }


def create_user(username: str, password_hash: str, email: str = None, exam_type: str = None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, email, exam_type, display_name) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (username, password_hash, email, exam_type, username)
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
            """
            SELECT u.id, u.username, u.role, u.email, u.display_name, u.created_at,
                   c.scores AS certificate_scores, c.average_score AS certificate_average,
                   c.grade AS certificate_grade, c.status AS certificate_status,
                   c.issued_at AS certificate_issued_at
            FROM users u
            LEFT JOIN certificates c ON c.user_id = u.id
            ORDER BY u.id
            """
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

CERTIFICATE_SCORE_FIELDS = ('web', 'pwn', 'crypto', 'reverse', 'forensics')


def get_certificate_by_user_id(user_id: int):
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT id, user_id, scores, average_score, grade, status,
                   file_name, issued_at, created_at, updated_at
            FROM certificates
            WHERE user_id = %s
            """,
            (user_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        put_conn(conn)


def create_or_update_certificate(user_id: int, scores: dict):
    average_score = round(sum(scores.values()) / len(scores), 2)
    if average_score >= 90:
        grade = 'A+'
    elif average_score >= 85:
        grade = 'A'
    elif average_score >= 80:
        grade = 'B+'
    elif average_score >= 70:
        grade = 'B'
    elif average_score >= 60:
        grade = 'C'
    else:
        grade = 'F'

    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            INSERT INTO certificates
                (user_id, scores, average_score, grade, status, file_name, issued_at, updated_at)
            VALUES (%s, %s, %s, %s, 'pending', NULL, NOW(), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                scores = EXCLUDED.scores,
                average_score = EXCLUDED.average_score,
                grade = EXCLUDED.grade,
                status = 'pending',
                file_name = NULL,
                issued_at = NOW(),
                updated_at = NOW()
            RETURNING id, user_id, scores, average_score, grade, status,
                      file_name, issued_at, created_at, updated_at
            """,
            (user_id, psycopg2.extras.Json(scores), average_score, grade)
        )
        row = cur.fetchone()
        conn.commit()
        return dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        put_conn(conn)


def mark_certificate_pending(certificate_id: int):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE certificates
            SET status = 'pending', file_name = NULL, issued_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """,
            (certificate_id,)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        put_conn(conn)


def update_certificate_status(certificate_id: int, status: str, file_name=None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE certificates
            SET status = %s, file_name = COALESCE(%s, file_name), updated_at = NOW()
            WHERE id = %s
            """,
            (status, file_name, certificate_id)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        put_conn(conn)
