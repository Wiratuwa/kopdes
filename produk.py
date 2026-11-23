"""Master produk: daftar (dengan search & filter), tambah, edit, hapus."""
from fastapi import APIRouter, Depends, Form, Request
from psycopg2 import errors

from core import admin_required, catat, flash, login_required, query, redirect, render

router = APIRouter(dependencies=[Depends(login_required)])


@router.get("/produk")
def produk_list(request: Request, q: str = "", stok_filter: str = "semua", sort: str = "kode_asc"):
    sql = "SELECT * FROM produk WHERE 1=1"
    params = []

    clean_q = q.strip()
    if clean_q:
        sql += " AND (LOWER(kode) LIKE %s OR LOWER(nama) LIKE %s)"
        kw = f"%{clean_q.lower()}%"
        params.extend([kw, kw])

    if stok_filter == "aman":
        sql += " AND stok >= stok_min"
    elif stok_filter == "menipis":
        sql += " AND stok > 0 AND stok < stok_min"
    elif stok_filter == "habis":
        sql += " AND stok = 0"

    sort_map = {
        "kode_asc": "kode ASC",
        "kode_desc": "kode DESC",
        "nama_asc": "nama ASC",
        "nama_desc": "nama DESC",
        "harga_asc": "harga ASC",
        "harga_desc": "harga DESC",
        "stok_asc": "stok ASC",
        "stok_desc": "stok DESC",
    }
    order_clause = sort_map.get(sort, "kode ASC")
    sql += f" ORDER BY {order_clause}"

    rows = query(sql, tuple(params))
    return render(
        request,
        "produk.html",
        rows=rows,
        q=clean_q,
        stok_filter=stok_filter,
        sort=sort,
        total=len(rows)
    )


@router.get("/produk/tambah", dependencies=[Depends(admin_required)])
def produk_tambah(request: Request):
    return render(request, "produk_form.html", p=None)


@router.post("/produk/tambah", dependencies=[Depends(admin_required)])
def produk_tambah_post(request: Request, kode: str = Form(...), nama: str = Form(...),
                       harga: int = Form(...), stok: int = Form(...), stok_min: int = Form(10),
                       harga_beli: str = Form("")):
    hb = int(harga_beli) if harga_beli.isdigit() else None
    if harga < 0 or stok < 0 or stok_min < 0:
        flash(request, "Harga, stok, dan batas stok tidak boleh negatif", "danger")
        return render(request, "produk_form.html", p=None)
    try:
        query("INSERT INTO produk (kode, nama, harga, stok, stok_min, harga_beli) VALUES (%s,%s,%s,%s,%s,%s)",
              (kode.strip().upper(), nama.strip(), harga, stok, stok_min, hb))
    except errors.UniqueViolation:
        flash(request, "Kode produk sudah dipakai", "danger")
        return render(request, "produk_form.html", p=None)
    catat(request, "tambah_produk", kode.strip().upper())
    flash(request, "Produk ditambahkan")
    return redirect("/produk")


@router.get("/produk/{id}/edit", dependencies=[Depends(admin_required)])
def produk_edit(request: Request, id: int):
    p = query("SELECT * FROM produk WHERE id=%s", (id,), one=True)
    if not p:
        return redirect("/produk")
    return render(request, "produk_form.html", p=p)


@router.post("/produk/{id}/edit", dependencies=[Depends(admin_required)])
def produk_edit_post(request: Request, id: int, kode: str = Form(...), nama: str = Form(...),
                     harga: int = Form(...), stok: int = Form(...), stok_min: int = Form(10),
                     harga_beli: str = Form("")):
    p = query("SELECT * FROM produk WHERE id=%s", (id,), one=True)
    if not p:
        return redirect("/produk")
    hb = int(harga_beli) if harga_beli.isdigit() else None
    if harga < 0 or stok < 0 or stok_min < 0:
        flash(request, "Harga, stok, dan batas stok tidak boleh negatif", "danger")
        return render(request, "produk_form.html", p=p)
    try:
        query("UPDATE produk SET kode=%s, nama=%s, harga=%s, stok=%s, stok_min=%s, harga_beli=%s WHERE id=%s",
              (kode.strip().upper(), nama.strip(), harga, stok, stok_min, hb, id))
    except errors.UniqueViolation:
        flash(request, "Kode produk sudah dipakai", "danger")
        return render(request, "produk_form.html", p=p)
    catat(request, "edit_produk", kode.strip().upper())
    flash(request, "Produk diperbarui")
    return redirect("/produk")


@router.post("/produk/{id}/hapus", dependencies=[Depends(admin_required)])
def produk_hapus(request: Request, id: int):
    try:
        query("DELETE FROM produk WHERE id=%s", (id,))
        catat(request, "hapus_produk", str(id))
        flash(request, "Produk dihapus")
    except errors.ForeignKeyViolation:
        flash(request, "Produk tidak bisa dihapus karena sudah dipakai di transaksi", "danger")
    return redirect("/produk")
