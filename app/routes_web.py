"""Rotas do portal web (HTML server-rendered, feed de ofertas com filtros)."""
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from app.db import get_session
from app.models import Offer

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def index(
    request: Request,
    q: str | None = Query(default=None, description="Busca por palavra-chave"),
    source_group: str | None = Query(default=None),
    days: int | None = Query(default=None, description="Só ofertas dos últimos N dias"),
):
    with get_session() as session:
        stmt = select(Offer).order_by(Offer.posted_at.desc())

        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                (Offer.product_name.like(like)) | (Offer.raw_text.like(like))
            )
        if source_group:
            stmt = stmt.where(Offer.source_group == source_group)
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            stmt = stmt.where(Offer.posted_at >= cutoff)

        offers = session.exec(stmt.limit(200)).all()

        groups = session.exec(
            select(Offer.source_group, Offer.source_label).distinct()
        ).all()

        # SQLModel não aceita atributos fora do schema declarado — construímos
        # um dict simples por oferta pra passar os links já decodificados ao
        # template, sem mexer no modelo.
        offers = [
            {**offer.model_dump(), "links_list": json.loads(offer.links or "[]")}
            for offer in offers
        ]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "offers": offers,
            "groups": groups,
            "q": q or "",
            "source_group": source_group or "",
            "days": days or "",
        },
    )
