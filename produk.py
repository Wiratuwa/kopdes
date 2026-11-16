"""Master produk: daftar, tambah, edit, hapus."""
from fastapi import APIRouter, Depends, Form, Request
from psycopg2 import errors

from core import flash, login_required, query, redirect, render

router = APIRouter(dependencies=[Depends(login_required)])


@router.get("/produk")
def produk_list(request: Request):
    return render(request, "produk.html", rows=query("SELECT * FROM produk ORDER BY kode"))


@router.get("/produk/tambah")
def produk_tambah(request: Request):
    return render(request, "produk_form.html", p=None)


@router.post("/produk/tambah")
def produk_tambah_post(request: Request, kode: str = Form(...), nama: str = Form(...),
                       harga: int = Form(...), stok: int = Form(...)):
    if harga < 0 or stok < 0:
        flash(request, "Harga dan stok tidak boleh negatif", "danger")
        return render(request, "produk_form.html", p=None)
    try:
        query("INSERT INTO produk (kode, nama, harga, stok) VALUES (%s,%s,%s,%s)",
              (kode.strip().upper(), nama.strip(), harga, stok))
    except errors.UniqueViolation:
        flash(request, "Kode produk sudah dipakai", "danger")
        return render(request, "produk_form.html", p=None)
    flash(request, "Produk ditambahkan")
    return redirect("/produk")


@router.get("/produk/{id}/edit")
def produk_edit(request: Request, id: int):
    p = query("SELECT * FROM produk WHERE id=%s", (id,), one=True)
    if not p:
        return redirect("/produk")
    return render(request, "produk_form.html", p=p)


@router.post("/produk/{id}/edit")
def produk_edit_post(request: Request, id: int, kode: str = Form(...), nama: str = Form(...),
                     harga: int = Form(...), stok: int = Form(...)):
    p = query("SELECT * FROM produk WHERE id=%s", (id,), one=True)
    if not p:
        return redirect("/produk")
    if harga < 0 or stok < 0:
        flash(request, "Harga dan stok tidak boleh negatif", "danger")
        return render(request, "produk_form.html", p=p)
    try:
        query("UPDATE produk SET kode=%s, nama=%s, harga=%s, stok=%s WHERE id=%s",
              (kode.strip().upper(), nama.strip(), harga, stok, id))
    except errors.UniqueViolation:
        flash(request, "Kode produk sudah dipakai", "danger")
        return render(request, "produk_form.html", p=p)
    flash(request, "Produk diperbarui")
    return redirect("/produk")


@router.post("/produk/{id}/hapus")
def produk_hapus(request: Request, id: int):
    try:
        query("DELETE FROM produk WHERE id=%s", (id,))
        flash(request, "Produk dihapus")
    except errors.ForeignKeyViolation:
        flash(request, "Produk tidak bisa dihapus karena sudah dipakai di transaksi", "danger")
    return redirect("/produk")
