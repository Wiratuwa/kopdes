"""Pelanggan/anggota: CRUD, riwayat nota, saldo kasbon, bayar cicilan."""
from fastapi import APIRouter, Depends, Form, Request
from psycopg2 import errors

from core import catat, flash, login_required, query, redirect, render, transaction

router = APIRouter(dependencies=[Depends(login_required)])

# saldo utang = total nota kasbon - total cicilan
SALDO = """COALESCE((SELECT SUM(total) FROM nota WHERE pelanggan_id = pl.id AND status = 'utang'), 0)
         - COALESCE((SELECT SUM(jumlah) FROM pembayaran_utang WHERE pelanggan_id = pl.id), 0)"""


@router.get("/pelanggan")
def pelanggan_list(request: Request):
    rows = query(f"SELECT pl.*, {SALDO} AS utang FROM pelanggan pl ORDER BY pl.nama")
    return render(request, "pelanggan.html", rows=rows)


@router.get("/pelanggan/tambah")
def pelanggan_tambah(request: Request):
    return render(request, "pelanggan_form.html", c=None)


@router.post("/pelanggan/tambah")
def pelanggan_tambah_post(request: Request, nama: str = Form(...), no_hp: str = Form(""),
                          alamat: str = Form("")):
    if not nama.strip():
        flash(request, "Nama tidak boleh kosong", "danger")
        return render(request, "pelanggan_form.html", c=None)
    query("INSERT INTO pelanggan (nama, no_hp, alamat) VALUES (%s,%s,%s)",
          (nama.strip(), no_hp.strip() or None, alamat.strip() or None))
    flash(request, "Pelanggan ditambahkan")
    return redirect("/pelanggan")


@router.get("/pelanggan/{id}")
def pelanggan_detail(request: Request, id: int):
    c = query(f"SELECT pl.*, {SALDO} AS utang FROM pelanggan pl WHERE pl.id=%s", (id,), one=True)
    if not c:
        return redirect("/pelanggan")
    nota = query("SELECT * FROM nota WHERE pelanggan_id=%s ORDER BY id DESC", (id,))
    bayar = query("SELECT * FROM pembayaran_utang WHERE pelanggan_id=%s ORDER BY id DESC", (id,))
    return render(request, "pelanggan_detail.html", c=c, nota=nota, bayar=bayar)


@router.get("/pelanggan/{id}/edit")
def pelanggan_edit(request: Request, id: int):
    c = query("SELECT * FROM pelanggan WHERE id=%s", (id,), one=True)
    if not c:
        return redirect("/pelanggan")
    return render(request, "pelanggan_form.html", c=c)


@router.post("/pelanggan/{id}/edit")
def pelanggan_edit_post(request: Request, id: int, nama: str = Form(...), no_hp: str = Form(""),
                        alamat: str = Form("")):
    if not nama.strip():
        flash(request, "Nama tidak boleh kosong", "danger")
        return redirect(f"/pelanggan/{id}/edit")
    query("UPDATE pelanggan SET nama=%s, no_hp=%s, alamat=%s WHERE id=%s",
          (nama.strip(), no_hp.strip() or None, alamat.strip() or None, id))
    flash(request, "Pelanggan diperbarui")
    return redirect(f"/pelanggan/{id}")


@router.post("/pelanggan/{id}/bayar")
def pelanggan_bayar(request: Request, id: int, jumlah: int = Form(...)):
    ok = False
    with transaction() as cur:
        cur.execute("SELECT id FROM pelanggan WHERE id=%s FOR UPDATE", (id,))  # cegah bayar ganda bersamaan
        if not cur.fetchone():
            return redirect("/pelanggan")
        cur.execute(f"SELECT {SALDO} AS utang FROM pelanggan pl WHERE pl.id=%s", (id,))
        utang = cur.fetchone()["utang"]
        if jumlah < 1 or jumlah > utang:
            flash(request, f"Jumlah harus 1 s/d sisa utang ({int(utang)})", "danger")
        else:
            cur.execute("INSERT INTO pembayaran_utang (pelanggan_id, jumlah, user_id) VALUES (%s,%s,%s)",
                        (id, jumlah, request.session["user_id"]))
            flash(request, "Pembayaran dicatat")
            ok = True
    if ok:
        catat(request, "bayar_utang", f"pelanggan {id}: {jumlah}")
    return redirect(f"/pelanggan/{id}")


@router.post("/pelanggan/{id}/hapus")
def pelanggan_hapus(request: Request, id: int):
    try:
        query("DELETE FROM pelanggan WHERE id=%s", (id,))
        flash(request, "Pelanggan dihapus")
        catat(request, "hapus_pelanggan", str(id))
    except errors.ForeignKeyViolation:
        flash(request, "Pelanggan punya riwayat transaksi/utang, tidak bisa dihapus", "danger")
    return redirect("/pelanggan")
