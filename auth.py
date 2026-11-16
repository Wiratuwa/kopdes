"""Halaman publik: index, register, login, logout."""
from fastapi import APIRouter, Form, Request
from psycopg2 import errors

from core import flash, hash_password, query, redirect, render, verify_password

router = APIRouter()


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
        query("INSERT INTO users (nama, email, password_hash) VALUES (%s,%s,%s)",
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
        request.session["user_id"], request.session["nama"] = u["id"], u["nama"]
        return redirect("/dashboard")
    flash(request, "Email atau password salah", "danger")
    return render(request, "login.html")


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")
