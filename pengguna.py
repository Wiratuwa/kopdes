"""Kelola pengguna (peran, aktif/nonaktif) dan log aktivitas — khusus admin."""
from fastapi import APIRouter, Depends, Form, Request

from core import admin_required, catat, flash, query, redirect, render

router = APIRouter(dependencies=[Depends(admin_required)])


@router.get("/pengguna")
def pengguna_list(request: Request):
    rows = query("SELECT id, nama, email, role, aktif, created_at FROM users ORDER BY id")
    return render(request, "pengguna.html", rows=rows, me=request.session["user_id"])


@router.post("/pengguna/{id}/role")
def pengguna_role(request: Request, id: int, role: str = Form(...)):
    if role not in ("admin", "kasir"):
        flash(request, "Peran tidak valid", "danger")
    elif id == request.session["user_id"]:
        flash(request, "Tidak bisa mengubah peran diri sendiri", "danger")
    else:
        query("UPDATE users SET role=%s WHERE id=%s", (role, id))
        catat(request, "ubah_role", f"user {id} -> {role}")
        flash(request, "Peran diperbarui")
    return redirect("/pengguna")


@router.post("/pengguna/{id}/aktif")
def pengguna_aktif(request: Request, id: int):
    if id == request.session["user_id"]:
        flash(request, "Tidak bisa menonaktifkan diri sendiri", "danger")
    else:
        u = query("UPDATE users SET aktif = NOT aktif WHERE id=%s RETURNING aktif", (id,), one=True)
        if u:
            catat(request, "aktif_user" if u["aktif"] else "nonaktif_user", f"user {id}")
            flash(request, "Status pengguna diperbarui")
    return redirect("/pengguna")


@router.get("/log")
def log_aktivitas(request: Request):
    rows = query("""SELECT l.*, u.nama FROM log_aktivitas l LEFT JOIN users u ON u.id = l.user_id
                    ORDER BY l.id DESC LIMIT 200""")
    return render(request, "log.html", rows=rows)
