"""Laporan penjualan per periode + export Excel."""
import io
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

from core import admin_required, query, render

router = APIRouter(dependencies=[Depends(admin_required)])


def ambil_laporan(dari: str, sampai: str):
    def parse(s, default):
        try:
            return date.fromisoformat(s)
        except ValueError:
            return default
    hari_ini = date.today()
    dari = parse(dari, hari_ini.replace(day=1))
    sampai = parse(sampai, hari_ini)
    rows = query("""SELECT t.*, p.kode, p.nama AS produk, p.harga_beli, u.nama AS kasir
                    FROM transaksi t
                    JOIN produk p ON p.id = t.produk_id
                    JOIN users u ON u.id = t.user_id
                    WHERE t.tanggal BETWEEN %s AND %s
                    ORDER BY t.tanggal, t.id""", (dari, sampai))
    return dari.isoformat(), sampai.isoformat(), rows


def ringkasan(rows):
    """Total per produk, per kasir, dan laba kotor (hanya baris yang harga belinya terisi)."""
    per_produk, per_kasir, laba, tanpa_hb = {}, {}, 0, 0
    for r in rows:
        a = per_produk.setdefault(r["produk"], [0, 0])
        a[0] += r["qty"]
        a[1] += r["total"]
        per_kasir[r["kasir"]] = per_kasir.get(r["kasir"], 0) + r["total"]
        if r["harga_beli"] is None:
            tanpa_hb += 1
        else:
            laba += r["total"] - r["qty"] * r["harga_beli"]
    return (sorted(per_produk.items(), key=lambda x: -x[1][1]),
            sorted(per_kasir.items(), key=lambda x: -x[1]), laba, tanpa_hb)


@router.get("/laporan")
def laporan(request: Request, dari: str = "", sampai: str = ""):
    dari, sampai, rows = ambil_laporan(dari, sampai)
    per_produk, per_kasir, laba, tanpa_hb = ringkasan(rows)
    return render(request, "laporan.html", dari=dari, sampai=sampai, rows=rows,
                  total=sum(r["total"] for r in rows), per_produk=per_produk,
                  per_kasir=per_kasir, laba=laba, tanpa_hb=tanpa_hb)


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
    per_produk, per_kasir, laba, _ = ringkasan(rows)
    ws2 = wb.create_sheet("Per Produk")
    ws2.append(["Produk", "Qty", "Total"])
    for nama, (q, t) in per_produk:
        ws2.append([nama, q, float(t)])
    ws3 = wb.create_sheet("Per Kasir")
    ws3.append(["Kasir", "Total"])
    for nama, t in per_kasir:
        ws3.append([nama, float(t)])
    ws3.append([])
    ws3.append(["Laba kotor (estimasi)", float(laba)])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=laporan_{dari}_{sampai}.xlsx"})
