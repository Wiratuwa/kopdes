"""Pengaturan Akun: edit nama, foto profil (PFP), dan ganti password."""
from fastapi import APIRouter, Depends, Form, Request

from core import flash, hash_password, login_required, query, redirect, render, verify_password

router = APIRouter(dependencies=[Depends(login_required)])


@router.get("/settings")
def settings_page(request: Request):
    user_id = request.session.get("user_id")
    u = query("SELECT id, nama, email, foto, created_at FROM users WHERE id=%s", (user_id,), one=True)
    if not u:
        return redirect("/logout")
    return render(request, "settings.html", u=u)


@router.post("/settings/profil")
def settings_profil_post(request: Request, nama: str = Form(...), foto: str = Form("")):
    user_id = request.session.get("user_id")
    clean_nama = nama.strip()
    if not clean_nama:
        flash(request, "Nama tidak boleh kosong", "danger")
        return redirect("/settings")

    clean_foto = foto.strip()
    query("UPDATE users SET nama=%s, foto=%s WHERE id=%s", (clean_nama, clean_foto or None, user_id))
    
    # Perbarui data di session pengguna
    request.session["nama"] = clean_nama
    request.session["foto"] = clean_foto or None

    flash(request, "Profil berhasil diperbarui!")
    return redirect("/settings")


@router.post("/settings/password")
def settings_password_post(request: Request,
                           current_password: str = Form(...),
                           new_password: str = Form(...),
                           confirm_password: str = Form(...)):
    user_id = request.session.get("user_id")
    u = query("SELECT * FROM users WHERE id=%s", (user_id,), one=True)
    if not u or not verify_password(current_password, u["password_hash"]):
        flash(request, "Password saat ini salah", "danger")
        return redirect("/settings")

    if len(new_password) < 6:
        flash(request, "Password baru minimal 6 karakter", "danger")
        return redirect("/settings")

    if new_password != confirm_password:
        flash(request, "Konfirmasi password baru tidak cocok", "danger")
        return redirect("/settings")

    query("UPDATE users SET password_hash=%s WHERE id=%s", (hash_password(new_password), user_id))
    flash(request, "Password berhasil diubah!")
    return redirect("/settings")

