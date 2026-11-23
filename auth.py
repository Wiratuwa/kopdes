"""Halaman publik: index, register, login, logout."""
import hashlib
import os
import secrets

from fastapi import APIRouter, Form, Request
from psycopg2 import errors

from core import (flash, hash_password, kirim_email, query, redirect, render, transaction,
                  verify_password)

router = APIRouter()


def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _token_valid(token):
    return query("""SELECT user_id FROM reset_token
                    WHERE token_hash=%s AND NOT used AND expires_at > NOW()""",
                 (_hash_token(token),), one=True)


@router.post("/lupa-password")
def lupa_password(request: Request, email: str = Form(...)):
    u = query("SELECT id, nama FROM users WHERE email=%s AND aktif", (email.strip().lower(),), one=True)
    if u:
        token = secrets.token_urlsafe(32)
        query("""INSERT INTO reset_token (user_id, token_hash, expires_at)
                 VALUES (%s,%s, NOW() + INTERVAL '1 hour')""", (u["id"], _hash_token(token)))
        # APP_URL dipakai (bukan header Host) supaya link tidak bisa dibelokkan penyerang
        link = os.environ.get("APP_URL", str(request.base_url)).rstrip("/") + f"/reset-password/{token}"
        kirim_email(email.strip(), "Penggantian password Kopdes Desa Aseli",
                    f"Halo {u['nama']},\n\nKlik link berikut untuk mengganti password (berlaku 1 jam):\n{link}\n\n"
                    "Abaikan email ini jika kamu tidak memintanya.")
    # pesan sama baik email terdaftar atau tidak, supaya email tidak bisa ditebak
    flash(request, "Jika email terdaftar, link penggantian password sudah dikirim. Cek inbox/spam.")
    return redirect("/login")


@router.get("/reset-password/{token}")
def reset_password(request: Request, token: str):
    if not _token_valid(token):
        flash(request, "Link tidak valid atau sudah kedaluwarsa", "danger")
        return redirect("/login")
    return render(request, "reset_password.html", token=token)


@router.post("/reset-password/{token}")
def reset_password_post(request: Request, token: str, password: str = Form(...),
                        konfirmasi: str = Form(...)):
    t = _token_valid(token)
    if not t:
        flash(request, "Link tidak valid atau sudah kedaluwarsa", "danger")
        return redirect("/login")
    if len(password) < 6:
        flash(request, "Password minimal 6 karakter", "danger")
        return render(request, "reset_password.html", token=token)
    if password != konfirmasi:
        flash(request, "Konfirmasi password tidak cocok", "danger")
        return render(request, "reset_password.html", token=token)
    with transaction() as cur:
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (hash_password(password), t["user_id"]))
        cur.execute("UPDATE reset_token SET used=TRUE WHERE user_id=%s", (t["user_id"],))
    flash(request, "Password berhasil diganti, silakan login")
    return redirect("/login")


@router.get("/")
def index(request: Request):
    return redirect("/dashboard" if "user_id" in request.session else "/login")


@router.get("/register")
def register(request: Request):
    return render(request, "register.html")


@router.post("/register")
def register_post(request: Request, nama: str = Form(...), email: str = Form(...),
                  password: str = Form(...)):
    if len(password) < 6:
        flash(request, "Password minimal 6 karakter", "danger")
        return render(request, "register.html")
    try:
        # user pertama otomatis admin, selanjutnya kasir
        query("""INSERT INTO users (nama, email, password_hash, role)
                 VALUES (%s,%s,%s, CASE WHEN EXISTS (SELECT 1 FROM users) THEN 'kasir' ELSE 'admin' END)""",
              (nama.strip(), email.strip().lower(), hash_password(password)))
    except errors.UniqueViolation:
        flash(request, "Email sudah terdaftar", "danger")
        return render(request, "register.html")
    flash(request, "Registrasi berhasil, silakan login")
    return redirect("/login")


@router.get("/login")
def login(request: Request):
    return render(request, "login.html")


@router.post("/login")
def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    u = query("SELECT * FROM users WHERE email=%s", (email.strip().lower(),), one=True)
    if u and verify_password(password, u["password_hash"]):
        if not u["aktif"]:
            flash(request, "Akun dinonaktifkan, hubungi admin", "danger")
            return render(request, "login.html")
        request.session["user_id"] = u["id"]
        request.session["role"] = u["role"]
        request.session["nama"] = u["nama"]
        request.session["foto"] = u.get("foto")
        return redirect("/dashboard")
    flash(request, "Email atau password salah", "danger")
    return render(request, "login.html", gagal_email=email.strip())  # login.html otomatis buka popup lupa password


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")
