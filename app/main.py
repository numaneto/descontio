"""Ponto de entrada da aplicação FastAPI (portal + webhook de ingestão)."""
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import MEDIA_DIR
from app.db import init_db
from app.routes_api import router as api_router
from app.routes_api_public import router as api_public_router
from app.routes_web import router as web_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="descont.io", description="Agregador pessoal de promoções")

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(web_router)
app.include_router(api_router)
app.include_router(api_public_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
