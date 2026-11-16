"""Transaksi penjualan: daftar, tambah (kurangi stok), hapus (kembalikan stok)."""
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request

from core import flash, login_required, query, redirect, render, transaction

router = APIRouter(dependencies=[Depends(login_required)])


@router.get("/transaksi")
def transaksi_list(request: Request):
    rows = query("""SELECT t.*, p.kode, p.nama AS produk, u.nama AS kasir
                    FROM transaksi t
                    JOIN produk p ON p.id = t.produk_id
                    JOIN users u ON u.id = t.user_id
                    ORDER BY t.id DESC""")
    return render(request, "transaksi.html", rows=rows)


def produk_tersedia():
    return query("SELECT * FROM produk WHERE stok > 0 ORDER BY nama")


@router.get("/transaksi/tambah")
def transaksi_tambah(request: Request):
    return render(request, "transaksi_form.html", produk=produk_tersedia())


@router.post("/transaksi/tambah")
def transaksi_tambah_post(request: Request, produk_id: int = Form(...), qty: int = Form(...)):
    with transaction() as cur:
        cur.execute("SELECT harga, stok FROM produk WHERE id=%s FOR UPDATE", (produk_id,))
        p = cur.fetchone()
        if not p or qty < 1:
            flash(request, "Data tidak valid", "danger")
        elif p["stok"] < qty:
            flash(request, f"Stok tidak cukup (sisa {p['stok']})", "danger")
        else:
            cur.execute("UPDATE produk SET stok = stok - %s WHERE id=%s", (qty, produk_id))
            no = datetime.now().strftime("TRX%Y%m%d-%H%M%S-") + secrets.token_hex(1).upper()
            cur.execute("""INSERT INTO transaksi (no_transaksi, user_id, produk_id, qty, harga, total)
                           VALUES (%s,%s,%s,%s,%s,%s)""",
                        (no, request.session["user_id"], produk_id, qty, p["harga"], p["harga"] * qty))
            flash(request, "Transaksi tersimpan")
            return redirect("/transaksi")
    return render(request, "transaksi_form.html", produk=produk_tersedia())


@router.post("/transaksi/{id}/hapus")
def transaksi_hapus(request: Request, id: int):
    with transaction() as cur:
        cur.execute("DELETE FROM transaksi WHERE id=%s RETURNING produk_id, qty", (id,))
        t = cur.fetchone()
        if t:  # kembalikan stok
            cur.execute("UPDATE produk SET stok = stok + %s WHERE id=%s", (t["qty"], t["produk_id"]))
            flash(request, "Transaksi dihapus, stok dikembalikan")
    return redirect("/transaksi")
