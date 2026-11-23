"""Transaksi penjualan: nota multi-item (+ kasbon), struk, hapus (kembalikan stok)."""
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request

from core import admin_required, catat, flash, login_required, query, redirect, render, transaction

router = APIRouter(dependencies=[Depends(login_required)])


@router.get("/transaksi")
def transaksi_list(request: Request):
    rows = query("""SELECT n.*, u.nama AS kasir, pl.nama AS pelanggan,
                           (SELECT string_agg(p.nama || ' x' || t.qty, ', ' ORDER BY t.id)
                            FROM transaksi t JOIN produk p ON p.id = t.produk_id
                            WHERE t.nota_id = n.id) AS items
                    FROM nota n
                    JOIN users u ON u.id = n.user_id
                    LEFT JOIN pelanggan pl ON pl.id = n.pelanggan_id
                    ORDER BY n.id DESC""")
    return render(request, "transaksi.html", rows=rows)


def _form(request):
    return render(request, "transaksi_form.html",
                  produk=query("SELECT * FROM produk WHERE stok > 0 ORDER BY nama"),
                  pelanggan=query("SELECT id, nama FROM pelanggan ORDER BY nama"))


@router.get("/transaksi/tambah")
def transaksi_tambah(request: Request):
    return _form(request)


@router.post("/transaksi/tambah")
def transaksi_tambah_post(request: Request, produk_id: list[int] = Form(...), qty: list[int] = Form(...),
                          pelanggan_id: str = Form(""), kasbon: str = Form("")):
    # gabungkan baris produk yang sama; urut id supaya urutan lock konsisten
    item = {}
    for pid, q in zip(produk_id, qty):
        item[pid] = item.get(pid, 0) + q
    pel = int(pelanggan_id) if pelanggan_id.isdigit() else None
    utang = bool(kasbon)
    if not item or min(item.values()) < 1:
        flash(request, "Data tidak valid", "danger")
    elif utang and pel is None:
        flash(request, "Kasbon wajib memilih pelanggan", "danger")
    else:
        with transaction() as cur:
            baris, total, ok = [], 0, True
            for pid in sorted(item):
                cur.execute("SELECT nama, harga, stok FROM produk WHERE id=%s FOR UPDATE", (pid,))
                p = cur.fetchone()
                if not p:
                    flash(request, "Produk tidak ditemukan", "danger")
                    ok = False
                elif p["stok"] < item[pid]:
                    flash(request, f"Stok {p['nama']} tidak cukup (sisa {p['stok']})", "danger")
                    ok = False
                else:
                    baris.append((pid, item[pid], p["harga"]))
                    total += p["harga"] * item[pid]
            if ok:
                no = datetime.now().strftime("TRX%Y%m%d-%H%M%S-") + secrets.token_hex(1).upper()
                cur.execute("""INSERT INTO nota (no_nota, user_id, pelanggan_id, status, total, bayar)
                               VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                            (no, request.session["user_id"], pel, "utang" if utang else "lunas",
                             total, 0 if utang else total))
                nota_id = cur.fetchone()["id"]
                for i, (pid, q, harga) in enumerate(baris, 1):
                    cur.execute("UPDATE produk SET stok = stok - %s WHERE id=%s", (q, pid))
                    cur.execute("""INSERT INTO transaksi (no_transaksi, nota_id, user_id, produk_id, qty, harga, total)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                                (f"{no}-{i}", nota_id, request.session["user_id"], pid, q, harga, harga * q))
                flash(request, "Transaksi tersimpan")
                return redirect(f"/transaksi/{nota_id}/struk")
    return _form(request)


@router.get("/transaksi/{id}/struk")
def transaksi_struk(request: Request, id: int):
    n = query("""SELECT n.*, u.nama AS kasir, pl.nama AS pelanggan
                 FROM nota n JOIN users u ON u.id = n.user_id
                 LEFT JOIN pelanggan pl ON pl.id = n.pelanggan_id WHERE n.id=%s""", (id,), one=True)
    if not n:
        return redirect("/transaksi")
    items = query("""SELECT t.qty, t.harga, t.total, p.nama FROM transaksi t
                     JOIN produk p ON p.id = t.produk_id WHERE t.nota_id=%s ORDER BY t.id""", (id,))
    return render(request, "struk.html", n=n, items=items)


@router.post("/transaksi/{id}/hapus", dependencies=[Depends(admin_required)])
def transaksi_hapus(request: Request, id: int):
    with transaction() as cur:
        cur.execute("DELETE FROM transaksi WHERE nota_id=%s RETURNING produk_id, qty", (id,))
        for t in cur.fetchall():  # kembalikan stok
            cur.execute("UPDATE produk SET stok = stok + %s WHERE id=%s", (t["qty"], t["produk_id"]))
        cur.execute("DELETE FROM nota WHERE id=%s RETURNING no_nota", (id,))
        n = cur.fetchone()
    if n:
        catat(request, "hapus_transaksi", n["no_nota"])
        flash(request, "Transaksi dihapus, stok dikembalikan")
    return redirect("/transaksi")
