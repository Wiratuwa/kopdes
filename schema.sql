-- Database: toko_kita (PostgreSQL)
-- Lokal : CREATE DATABASE toko_kita;  lalu  psql -d toko_kita -f schema.sql
-- Cloud : tempel isi file ini di SQL Editor (Neon / Supabase)

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    nama          VARCHAR(100) NOT NULL,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash TEXT         NOT NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- FILE MASTER
CREATE TABLE IF NOT EXISTS produk (
    id         SERIAL PRIMARY KEY,
    kode       VARCHAR(20)   NOT NULL UNIQUE,
    nama       VARCHAR(150)  NOT NULL,
    harga      NUMERIC(12,2) NOT NULL CHECK (harga >= 0),
    stok       INTEGER       NOT NULL DEFAULT 0 CHECK (stok >= 0),
    created_at TIMESTAMP     NOT NULL DEFAULT NOW()
);

-- FILE TRANSAKSI
CREATE TABLE IF NOT EXISTS transaksi (
    id           SERIAL PRIMARY KEY,
    no_transaksi VARCHAR(30)   NOT NULL UNIQUE,
    tanggal      DATE          NOT NULL DEFAULT CURRENT_DATE,
    user_id      INTEGER       NOT NULL REFERENCES users(id),
    produk_id    INTEGER       NOT NULL REFERENCES produk(id) ON DELETE RESTRICT,
    qty          INTEGER       NOT NULL CHECK (qty > 0),
    harga        NUMERIC(12,2) NOT NULL,
    total        NUMERIC(14,2) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transaksi_tanggal ON transaksi(tanggal);

-- Data contoh
INSERT INTO produk (kode, nama, harga, stok) VALUES
    ('P001', 'Beras 5 kg',       68000,  40),
    ('P002', 'Minyak Goreng 1L', 18000,  60),
    ('P003', 'Gula Pasir 1 kg',  17000,  35),
    ('P004', 'Telur 1 kg',       29000,  25),
    ('P005', 'Kopi Sachet',       2000, 200)
ON CONFLICT (kode) DO NOTHING;


SELECT * FROM produk;
