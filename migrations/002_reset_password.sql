-- Token reset password (idempotent). Yang disimpan hanya hash token, bukan token aslinya.
CREATE TABLE IF NOT EXISTS reset_token (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash CHAR(64)    NOT NULL UNIQUE,
    expires_at TIMESTAMP   NOT NULL,
    used       BOOLEAN     NOT NULL DEFAULT FALSE
);
