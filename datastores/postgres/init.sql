CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    email VARCHAR(255),
    display_name VARCHAR(100),
    exam_type VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- init.sql 只有在 pgdata volume 第一次建立時才會執行；
-- 如果是既有的 volume（沒有 exam_type 欄位），這行讓它可以補上去。
ALTER TABLE users ADD COLUMN IF NOT EXISTS exam_type VARCHAR(20);