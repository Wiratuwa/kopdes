"""Laporan penjualan per periode + export Excel."""
import io
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

from core import login_required, query, render

router = APIRouter(dependencies=[Depends(login_required)])


def ambil_laporan(dari: str, sampai: str):
    def parse(s, default):
        try:
            return date.fromisoformat(s)
        except ValueError:
            return default
    hari_ini = date.today()
    dari = parse(dari, hari_ini.replace(day=1))
    sampai = parse(sampai, hari_ini)
    rows = query("""SELECT t.*, p.kode, p.nama AS produk, u.nama AS kasir
                    FROM transaksi t
                    JOIN produk p ON p.id = t.produk_id
                    JOIN users u ON u.id = t.user_id
                    WHERE t.tanggal BETWEEN %s AND %s
                    ORDER BY t.tanggal, t.id""", (dari, sampai))
    return dari.isoformat(), sampai.isoformat(), rows


@router.get("/laporan")
def laporan(request: Request, dari: str = "", sampai: str = ""):
    dari, sampai, rows = ambil_laporan(dari, sampai)
    return render(request, "laporan.html", dari=dari, sampai=sampai, rows=rows,
                  total=sum(r["total"] for r in rows))


@router.get("/laporan/excel")
def laporan_excel(dari: str = "", sampai: str = ""):
    dari, sampai, rows = ambil_laporan(dari, sampai)
    wb = Workbook()
    ws = wb.active
    ws.title = "Laporan Penjualan"
    ws.append(["No Transaksi", "Tanggal", "Kode", "Produk", "Qty", "Harga", "Total", "Kasir"])
    for r in rows:
        ws.append([r["no_transaksi"], r["tanggal"], r["kode"], r["produk"],
                   r["qty"], float(r["harga"]), float(r["total"]), r["kasir"]])
    ws.append([])
    ws.append(["", "", "", "", "", "Total", float(sum(r["total"] for r in rows))])
    for col, w in zip("ABCDEFGH", (24, 12, 8, 24, 6, 12, 14, 18)):
        ws.column_dimensions[col].width = w
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=laporan_{dari}_{sampai}.xlsx"})
