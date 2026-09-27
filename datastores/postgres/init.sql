CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    email VARCHAR(255),
    display_name VARCHAR(100) DEFAULT NULL,
    exam_type VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Display Name 預設為帳號名稱，並補齊既有資料。
UPDATE users SET display_name = username WHERE display_name IS NULL OR BTRIM(display_name) = '';

CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

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
);
