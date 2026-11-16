"""Halaman dashboard (wajib login) dengan grafik penjualan terlaris per minggu."""
import calendar
from datetime import date
from fastapi import APIRouter, Depends, Request

from core import login_required, query, render

router = APIRouter(dependencies=[Depends(login_required)])

BULAN_INDONESIA = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]


@router.get("/dashboard")
def dashboard(request: Request, bulan: int = None, tahun: int = None):
    today = date.today()
    if not bulan or not (1 <= bulan <= 12):
        bulan = today.month
    if not tahun or not (2020 <= tahun <= 2030):
        tahun = today.year

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

    # Query produk paling banyak terjual per minggu dalam 1 bulan yang dipilih
    weekly_raw = query("""
        WITH weekly_sales AS (
            SELECT
                CEIL(EXTRACT(DAY FROM t.tanggal) / 7.0)::int AS minggu,
                p.id AS produk_id,
                p.nama AS produk_nama,
                SUM(t.qty)::int AS total_qty,
                SUM(t.total) AS total_nominal,
                ROW_NUMBER() OVER (
                    PARTITION BY CEIL(EXTRACT(DAY FROM t.tanggal) / 7.0)
                    ORDER BY SUM(t.qty) DESC, SUM(t.total) DESC
                ) AS rn
            FROM transaksi t
            JOIN produk p ON p.id = t.produk_id
            WHERE EXTRACT(MONTH FROM t.tanggal) = %s AND EXTRACT(YEAR FROM t.tanggal) = %s
            GROUP BY CEIL(EXTRACT(DAY FROM t.tanggal) / 7.0), p.id, p.nama
        )
        SELECT minggu, produk_id, produk_nama, total_qty, total_nominal
        FROM weekly_sales
        WHERE rn = 1
        ORDER BY minggu;
    """, (bulan, tahun))

    sales_by_week = {row["minggu"]: row for row in weekly_raw}

    # Hitung jumlah hari dalam bulan tersebut
    _, days_in_month = calendar.monthrange(tahun, bulan)
    total_weeks = 5 if days_in_month > 28 else 4

    weekly_data = []
    chart_labels = []
    chart_values = []
    chart_products = []
    chart_totals = []

    for w in range(1, total_weeks + 1):
        start_day = (w - 1) * 7 + 1
        end_day = min(w * 7, days_in_month)
        label_range = f"Tgl {start_day} - {end_day} {BULAN_INDONESIA[bulan][:3]}"
        label_week = f"Minggu {w}"

        item = sales_by_week.get(w)
        if item:
            prod_name = item["produk_nama"]
            qty = int(item["total_qty"])
            nom = float(item["total_nominal"])
        else:
            prod_name = "Belum ada transaksi"
            qty = 0
            nom = 0.0

        weekly_data.append({
            "minggu": w,
            "label_minggu": label_week,
            "range": label_range,
            "produk": prod_name,
            "qty": qty,
            "nominal": nom,
            "has_sales": item is not None
        })

        chart_labels.append(label_week)
        chart_values.append(qty)
        chart_products.append(prod_name)
        chart_totals.append(nom)

    nama_bulan = BULAN_INDONESIA[bulan]

    return render(
        request,
        "dashboard.html",
        s=s,
        menipis=menipis,
        terakhir=terakhir,
        selected_bulan=bulan,
        selected_tahun=tahun,
        nama_bulan=nama_bulan,
        weekly_data=weekly_data,
        chart_labels=chart_labels,
        chart_values=chart_values,
        chart_products=chart_products,
        chart_totals=chart_totals,
        bulan_list=[(i, BULAN_INDONESIA[i]) for i in range(1, 13)],
        tahun_list=list(range(2023, today.year + 2))
    )
