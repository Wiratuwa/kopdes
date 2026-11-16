"""Titik masuk: rakit app dari modul per fitur. Jalankan: uvicorn main:app --reload"""
import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware  # session cookie, ditandatangani itsdangerous

import auth
import dashboard
import laporan
import produk
import transaksi
from core import BASE, NotLoggedIn, redirect, templates

app = FastAPI(title="Kopdes Desa Aseli")
app.add_middleware(SessionMiddleware,
                   secret_key=os.environ.get("SECRET_KEY", "ganti-di-production"),
                   max_age=60 * 60 * 8)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

# url_for versi path relatif (aman di belakang proxy HTTPS hosting)
templates.env.globals["url_for"] = lambda name, **kw: str(app.url_path_for(name, **kw))


@app.exception_handler(NotLoggedIn)
async def _belum_login(request: Request, exc: NotLoggedIn):
    return redirect("/login")


for modul in (auth, dashboard, produk, transaksi, laporan):
    app.include_router(modul.router)
