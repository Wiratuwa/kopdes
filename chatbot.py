"""AI Chatbot helper — Gemini 2.0 Flash Lite via REST API (gratis)."""
import json
import os
import urllib.request

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from core import login_required, query

router = APIRouter(dependencies=[Depends(login_required)])

SYSTEM_PROMPT = """Kamu adalah asisten AI bernama "Aseli Bot" untuk aplikasi "Kopdes Desa Aseli", \
sebuah sistem Point of Sale (POS) untuk koperasi desa. Kamu ramah, membantu, dan selalu \
menjawab dalam Bahasa Indonesia. Gunakan emoji sesekali agar terasa ramah.

## Fitur Aplikasi:
1. **Dashboard** (/dashboard) — Ringkasan: total produk, stok menipis, transaksi hari ini, \
pendapatan hari ini, dan grafik penjualan mingguan (produk terlaris per minggu dalam 1 bulan).
2. **Master Produk** (/produk) — Kelola daftar barang: tambah, edit, hapus produk. \
Bisa search nama/kode, filter stok (aman/menipis/habis), dan sorting berbagai kolom.
3. **Transaksi** (/transaksi) — Catat penjualan baru: pilih produk, masukkan jumlah, \
stok otomatis berkurang. Lihat riwayat semua transaksi.
4. **Laporan** (/laporan) — Rekap penjualan per periode tanggal. Bisa diekspor ke file Excel (.xlsx).
5. **Pengaturan** (/settings) — Edit profil (nama, foto profil/emoji avatar), ganti password.

## Cara Menggunakan Website:
- **Login/Daftar**: Buka website → halaman login muncul. Masukkan email & password. \
Belum punya akun? Klik link "Daftar" di bawah form login.
- **Tambah Produk Baru**: Setelah login → klik menu "Master Produk" di navbar → \
klik tombol "Tambah Produk" → isi Kode Produk, Nama, Harga Jual, Stok Awal → klik "Simpan".
- **Catat Penjualan**: Klik menu "Transaksi" → klik "Transaksi Baru" → pilih produk dari dropdown, \
isi jumlah yang dijual → klik "Simpan". Stok otomatis berkurang sesuai jumlah.
- **Lihat Grafik Penjualan**: Klik menu "Dashboard" → scroll ke bawah, ada grafik bar chart \
yang menampilkan produk terlaris per minggu. Pilih bulan & tahun untuk filter.
- **Cari/Filter Produk**: Di halaman "Master Produk" ada kolom pencarian dan filter. \
Ketik nama/kode produk, atau filter berdasarkan status stok (Semua/Aman/Menipis/Habis).
- **Export Laporan ke Excel**: Klik menu "Laporan" → pilih tanggal awal & akhir → \
klik "Tampilkan" → klik tombol "Export Excel" untuk download file .xlsx.
- **Edit Profil**: Klik nama kamu di navbar (atau tombol "Pengaturan") → \
ubah nama, pilih emoji avatar atau upload foto → klik "Simpan Profil".
- **Ganti Password**: Di halaman Pengaturan → scroll ke bagian "Ganti Password" → \
isi password lama, password baru (min 6 karakter), konfirmasi → klik "Ubah Password".

## Aturan:
- Jawab secara RINGKAS dan jelas (maksimal 3-4 paragraf pendek).
- Jika user bertanya tentang data produk/stok/penjualan, gunakan data konteks yang diberikan.
- Jika tidak yakin, katakan jujur dan sarankan user mengecek langsung di menu terkait.
- Jangan pernah membagikan informasi teknis internal (database, API key, dll).
"""


class ChatRequest(BaseModel):
    message: str
    history: list = []


def _build_context():
    """Ambil ringkasan data terkini dari database untuk konteks chatbot."""
    parts = []

    # Daftar produk
    products = query("SELECT kode, nama, harga, stok FROM produk ORDER BY nama LIMIT 50")
    if products:
        lines = [f"  • {p['nama']} ({p['kode']}) — Rp{p['harga']:,.0f}, stok: {p['stok']}"
                 for p in products]
        parts.append("DAFTAR PRODUK:\n" + "\n".join(lines))

    # Produk stok menipis
    low = query("SELECT nama, stok FROM produk WHERE stok <= 5 ORDER BY stok")
    if low:
        lines = [f"  ⚠ {p['nama']}: sisa {p['stok']}" for p in low]
        parts.append("STOK MENIPIS (≤5):\n" + "\n".join(lines))
    else:
        parts.append("STOK MENIPIS: Tidak ada produk yang stoknya menipis.")

    # Penjualan 30 hari terakhir
    sales = query("""
        SELECT p.nama,
               SUM(t.qty)   AS total_jual,
               SUM(t.total) AS total_pendapatan
        FROM transaksi t
        JOIN produk p ON t.produk_id = p.id
        WHERE t.tanggal >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY p.nama
        ORDER BY total_jual DESC
        LIMIT 10
    """)
    if sales:
        lines = [f"  • {s['nama']}: {s['total_jual']} terjual, Rp{s['total_pendapatan']:,.0f}"
                 for s in sales]
        parts.append("PENJUALAN 30 HARI TERAKHIR (Top 10):\n" + "\n".join(lines))
    else:
        parts.append("PENJUALAN 30 HARI TERAKHIR: Belum ada data transaksi.")

    return "\n\n".join(parts)


@router.post("/api/chat")
async def chat_api(request: Request, body: ChatRequest):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return {"reply": "⚠️ API Key Gemini belum dikonfigurasi. Hubungi admin untuk menambahkan GEMINI_API_KEY."}

    # Bangun conversation contents
    contents = []
    for msg in body.history[-10:]:  # batasi history 10 pesan terakhir
        role = "model" if msg.get("role") == "model" else "user"
        contents.append({"role": role, "parts": [{"text": msg.get("text", "")}]})

    # Tambahkan pesan user + konteks data
    try:
        ctx = _build_context()
    except Exception:
        ctx = "(Data tidak dapat diambil saat ini)"

    user_text = body.message.strip()
    contents.append({
        "role": "user",
        "parts": [{"text": f"{user_text}\n\n---\n[Data Terkini Koperasi]\n{ctx}"}]
    })

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.0-flash-lite:generateContent?key={api_key}"
    )
    payload = json.dumps({
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
    }).encode()

    req = urllib.request.Request(url, data=payload,
                                headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        reply = data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        reply = f"Maaf, terjadi kesalahan dari Gemini API ({e.code}). Coba lagi nanti. 🙏"
    except Exception as e:
        reply = "Maaf, terjadi kesalahan koneksi. Coba lagi nanti. 🙏"

    return {"reply": reply}
