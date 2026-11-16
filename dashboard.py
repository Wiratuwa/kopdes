"""Halaman dashboard (wajib login)."""
from fastapi import APIRouter, Depends, Request

from core import login_required, query, render

router = APIRouter(dependencies=[Depends(login_required)])


@router.get("/dashboard")
def dashboard(request: Request):
    s = query("""
        SELECT (SELECT COUNT(*) FROM produk) AS jml_produk,
               (SELECT COUNT(*) FROM transaksi) AS jml_transaksi,
               (SELECT COALESCE(SUM(total),0) FROM transaksi WHERE tanggal = CURRENT_DATE) AS omzet_hari_ini,
               (SELECT COALESCE(SUM(total),0) FROM transaksi) AS omzet_total
    """, one=True)
    menipis = query("SELECT * FROM produk WHERE stok < 10 ORDER BY stok LIMIT 5")
    terakhir = query("""SELECT t.*, p.nama AS produk FROM transaksi t
                        JOIN produk p ON p.id = t.produk_id
                        ORDER BY t.id DESC LIMIT 5""")
    return render(request, "dashboard.html", s=s, menipis=menipis, terakhir=terakhir)
