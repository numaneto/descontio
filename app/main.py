"""Ponto de entrada da aplicação FastAPI."""
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import MEDIA_DIR
from app.db import init_db
from app.routes_admin import router as admin_router
from app.routes_api_public import router as api_public_router
from app.routes_web import router as web_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="descont.io", description="Portal e API de ofertas e descontos")

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(web_router)
app.include_router(api_public_router)
app.include_router(admin_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
