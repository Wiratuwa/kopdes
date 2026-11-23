"""Konfigurasi, database, dan helper yang dipakai semua halaman."""
import hashlib
import hmac
import os
import secrets
import smtplib
from email.message import EmailMessage
from contextlib import contextmanager
from pathlib import Path

import psycopg2
import psycopg2.extras
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

BASE = Path(__file__).parent

# Baca file .env dan .env.local kalau ada (untuk laptop / dev). Di hosting, pakai environment variable.
for env_name in (".env", ".env.local"):
    _env = BASE / env_name
    if _env.exists():
        for line in _env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

# Pastikan DATABASE_URL tersedia (fallback ke DATABASE_URL_UNPOOLED jika ada)
if "DATABASE_URL" not in os.environ and "DATABASE_URL_UNPOOLED" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL_UNPOOLED"]

templates = Jinja2Templates(directory=str(BASE / "templates"))


# ---------- Database ----------
@contextmanager
def transaction():
    """Satu transaksi DB: commit kalau sukses, rollback kalau error."""
    conn = psycopg2.connect(os.environ["DATABASE_URL"],
                            cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql, params=(), one=False):
    with transaction() as cur:
        cur.execute(sql, params)
        if cur.description:
            return cur.fetchone() if one else cur.fetchall()


# ---------- Helper ----------
def rupiah(v):
    return "Rp " + "{:,.0f}".format(v or 0).replace(",", ".")


templates.env.filters["rp"] = rupiah
# ikon Bootstrap Icons: {{ ic('trash') }}
templates.env.globals["ic"] = lambda n: Markup(f'<i class="bi bi-{n}" aria-hidden="true"></i>')


def hash_password(pw):
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${h}"


def verify_password(pw, stored):
    salt, h = stored.split("$")
    cek = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()
    return hmac.compare_digest(cek, h)


def flash(request: Request, msg, cat="success"):
    request.session.setdefault("flash", []).append([cat, msg])


def render(request: Request, name, **ctx):
    ctx["flashes"] = request.session.pop("flash", [])
    ctx["user"] = request.session.get("nama")
    ctx["user_foto"] = request.session.get("foto")
    ctx["role"] = request.session.get("role")
    return templates.TemplateResponse(request, name, ctx)


def redirect(url):
    return RedirectResponse(url, status_code=303)


# ---------- Wajib login ----------
class NotLoggedIn(Exception):
    pass


def login_required(request: Request):
    if "user_id" not in request.session:
        raise NotLoggedIn()


def kirim_email(to, subjek, isi):
    """Kirim email lewat Gmail SMTP (SMTP_USER + SMTP_PASSWORD = App Password). True kalau terkirim."""
    user, pw = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    if not (user and pw):
        print("kirim_email: SMTP_USER/SMTP_PASSWORD belum diatur")
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = os.environ.get("SMTP_FROM", user), to, subjek
    msg.set_content(isi)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(user, pw)
            s.send_message(msg)
        return True
    except Exception as e:  # jangan bocorkan error ke user; cukup log
        print(f"kirim_email gagal: {e!r}")
        return False


class Forbidden(Exception):
    pass


def admin_required(request: Request):
    login_required(request)
    if request.session.get("role") != "admin":
        flash(request, "Akses khusus admin", "danger")
        raise Forbidden()


def catat(request: Request, aksi, detail=""):
    """Tulis log aktivitas user yang sedang login."""
    query("INSERT INTO log_aktivitas (user_id, aksi, detail) VALUES (%s,%s,%s)",
          (request.session.get("user_id"), aksi, detail))
