# Kopdes Desa Asli - CRUD FastAPI + PostgreSQL

Paket: fastapi, uvicorn, jinja2, psycopg2-binary, python-multipart, itsdangerous, openpyxl

## Struktur
- main.py          : semua route (auth, dashboard, master produk, transaksi, laporan)
- schema.sql       : struktur database + data contoh
- templates/       : halaman HTML (Jinja2)

## Jalankan di laptop
1. Buat database:  createdb toko_kita   lalu   psql -d toko_kita -f schema.sql
2. python -m venv venv
   Windows : venv\Scripts\activate        Mac/Linux : source venv/bin/activate
3. pip install -r requirements.txt
4. Salin .env.example jadi .env, lalu isi DATABASE_URL dan SECRET_KEY
5. uvicorn main:app --reload
6. Buka http://127.0.0.1:8000

## Deploy gratis (Python + PostgreSQL)
Database - Neon (neon.tech):
1. Buat project, salin connection string (berakhiran ?sslmode=require)
2. Buka SQL Editor, tempel isi schema.sql, jalankan

Aplikasi - Render (render.com):
1. Upload folder ini ke repo GitHub
2. New > Web Service > pilih repo
3. Build Command : pip install -r requirements.txt
4. Start Command : uvicorn main:app --host 0.0.0.0 --port $PORT
5. Environment: DATABASE_URL (connection string Neon), SECRET_KEY (string acak panjang)

Kalau build gagal di psycopg2-binary, tambahkan environment variable PYTHON_VERSION = 3.12.3
