"""Stok masuk dari supplier (khusus admin): menambah stok dan mencatat harga beli."""
from fastapi import APIRouter, Depends, Form, Request

from core import admin_required, catat, flash, query, redirect, render, transaction

router = APIRouter(dependencies=[Depends(admin_required)])


def _form(request, produk_id=None):
    return render(request, "stok_masuk_form.html", produk_id=produk_id,
                  produk=query("SELECT id, kode, nama, stok FROM produk ORDER BY nama"))


@router.get("/stok-masuk")
def stok_masuk_list(request: Request):
    rows = query("""SELECT s.*, p.kode, p.nama AS produk, u.nama AS petugas
                    FROM stok_masuk s JOIN produk p ON p.id = s.produk_id
                    JOIN users u ON u.id = s.user_id ORDER BY s.id DESC LIMIT 200""")
    return render(request, "stok_masuk.html", rows=rows)


@router.get("/stok-masuk/tambah")
def stok_masuk_tambah(request: Request, produk_id: int = None):
    return _form(request, produk_id)


@router.post("/stok-masuk/tambah")
def stok_masuk_tambah_post(request: Request, produk_id: int = Form(...), qty: int = Form(...),
                           harga_beli: int = Form(...), supplier: str = Form("")):
    if qty < 1 or harga_beli < 0:
        flash(request, "Jumlah minimal 1 dan harga beli tidak boleh negatif", "danger")
        return _form(request, produk_id)
    with transaction() as cur:
        cur.execute("UPDATE produk SET stok = stok + %s, harga_beli = %s WHERE id=%s RETURNING nama",
                    (qty, harga_beli, produk_id))
        p = cur.fetchone()
        if not p:
            flash(request, "Produk tidak ditemukan", "danger")
            return _form(request)
        cur.execute("""INSERT INTO stok_masuk (produk_id, qty, harga_beli, supplier, user_id)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (produk_id, qty, harga_beli, supplier.strip() or None, request.session["user_id"]))
    catat(request, "stok_masuk", f"{p['nama']} +{qty}")
    flash(request, f"Stok {p['nama']} bertambah {qty}")
    return redirect("/stok-masuk")
