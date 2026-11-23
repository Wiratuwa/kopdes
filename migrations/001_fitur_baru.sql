-- Migrasi idempotent: aman dijalankan berulang. Jalankan di SQL Editor Neon (uji dulu di branch).

-- Peran user + status aktif + foto (kolom foto dipakai kode tapi belum ada di schema lama)
ALTER TABLE users ADD COLUMN IF NOT EXISTS foto  TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS role  VARCHAR(10) NOT NULL DEFAULT 'kasir' CHECK (role IN ('admin','kasir'));
ALTER TABLE users ADD COLUMN IF NOT EXISTS aktif BOOLEAN NOT NULL DEFAULT TRUE;
-- user pertama jadi admin kalau belum ada admin
UPDATE users SET role = 'admin'
WHERE id = (SELECT MIN(id) FROM users) AND NOT EXISTS (SELECT 1 FROM users WHERE role = 'admin');

-- Produk: harga beli (untuk laba) dan ambang stok menipis per produk
ALTER TABLE produk ADD COLUMN IF NOT EXISTS harga_beli NUMERIC(12,2) CHECK (harga_beli >= 0);
ALTER TABLE produk ADD COLUMN IF NOT EXISTS stok_min   INTEGER NOT NULL DEFAULT 10 CHECK (stok_min >= 0);

-- Pelanggan / anggota
CREATE TABLE IF NOT EXISTS pelanggan (
    id         SERIAL PRIMARY KEY,
    nama       VARCHAR(100) NOT NULL,
    no_hp      VARCHAR(20),
    alamat     TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Nota = header transaksi (1 nota punya banyak baris di tabel transaksi)
CREATE TABLE IF NOT EXISTS nota (
    id           SERIAL PRIMARY KEY,
    no_nota      VARCHAR(30)   NOT NULL UNIQUE,
    tanggal      DATE          NOT NULL DEFAULT CURRENT_DATE,
    user_id      INTEGER       NOT NULL REFERENCES users(id),
    pelanggan_id INTEGER       REFERENCES pelanggan(id) ON DELETE RESTRICT,
    status       VARCHAR(10)   NOT NULL DEFAULT 'lunas' CHECK (status IN ('lunas','utang')),
    total        NUMERIC(14,2) NOT NULL DEFAULT 0,
    bayar        NUMERIC(14,2) NOT NULL DEFAULT 0
);
ALTER TABLE transaksi ADD COLUMN IF NOT EXISTS nota_id INTEGER REFERENCES nota(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_transaksi_nota ON transaksi(nota_id);

-- Backfill: tiap baris transaksi lama jadi 1 nota
INSERT INTO nota (no_nota, tanggal, user_id, total, bayar)
SELECT no_transaksi, tanggal, user_id, total, total FROM transaksi WHERE nota_id IS NULL
ON CONFLICT (no_nota) DO NOTHING;
UPDATE transaksi t SET nota_id = n.id FROM nota n WHERE t.nota_id IS NULL AND n.no_nota = t.no_transaksi;

-- Cicilan utang pelanggan
CREATE TABLE IF NOT EXISTS pembayaran_utang (
    id           SERIAL PRIMARY KEY,
    pelanggan_id INTEGER       NOT NULL REFERENCES pelanggan(id) ON DELETE RESTRICT,
    jumlah       NUMERIC(14,2) NOT NULL CHECK (jumlah > 0),
    tanggal      DATE          NOT NULL DEFAULT CURRENT_DATE,
    user_id      INTEGER       NOT NULL REFERENCES users(id)
);

-- Stok masuk dari supplier
CREATE TABLE IF NOT EXISTS stok_masuk (
    id         SERIAL PRIMARY KEY,
    tanggal    DATE          NOT NULL DEFAULT CURRENT_DATE,
    produk_id  INTEGER       NOT NULL REFERENCES produk(id) ON DELETE RESTRICT,
    qty        INTEGER       NOT NULL CHECK (qty > 0),
    harga_beli NUMERIC(12,2) NOT NULL CHECK (harga_beli >= 0),
    supplier   VARCHAR(100),
    user_id    INTEGER       NOT NULL REFERENCES users(id)
);

-- Log aktivitas
CREATE TABLE IF NOT EXISTS log_aktivitas (
    id      SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    aksi    VARCHAR(40) NOT NULL,
    detail  TEXT,
    waktu   TIMESTAMP NOT NULL DEFAULT NOW()
);
