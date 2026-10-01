"""Rotas do portal web (HTML server-rendered, feed de ofertas com filtros)."""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from app.db import get_session
from app.models import Category
from app.money import format_brl
from app.offers_query import (
    DAYS_PRESETS,
    parse_days,
    parse_price,
    query_offers,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Todos os timestamps são armazenados em UTC (posted_at vem do Telethon ou
# de datetime.utcnow()) — a exibição precisa converter pro fuso do usuário
# (Brasil não tem horário de verão desde 2019, então America/Sao_Paulo é
# sempre UTC-3, sem ambiguidade de DST).
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")


def _to_local(value: datetime) -> str:
    """Converte um datetime (naive ou aware, assumido UTC se naive) pro
    fuso local e formata — usado como filtro Jinja (`| local_time`)."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M")


templates.env.filters["local_time"] = _to_local
templates.env.filters["brl"] = format_brl


@router.get("/")
def index(
    request: Request,
    q: str | None = Query(default=None, description="Busca por palavra-chave (aceita múltiplos termos)"),
    category: str | None = Query(default=None, description="Slug da categoria"),
    days: str | None = Query(default=None, description="Só ofertas dos últimos N dias (1-365)"),
    price_min: str | None = Query(default=None, description="Preço mínimo (R$)"),
    price_max: str | None = Query(default=None, description="Preço máximo (R$)"),
):
    days_int = parse_days(days)
    price_min_cents = parse_price(price_min)
    price_max_cents = parse_price(price_max)
    # Preço mínimo maior que o máximo não faz sentido — ignora os dois em
    # vez de devolver sempre um resultado vazio sem explicação nenhuma.
    if (
        price_min_cents is not None
        and price_max_cents is not None
        and price_min_cents > price_max_cents
    ):
        price_min_cents = price_max_cents = None

    with get_session() as session:
        categories = session.exec(select(Category).order_by(Category.name)).all()
        offers = query_offers(
            session,
            q=q,
            category_slug=category,
            days_int=days_int,
            price_min_cents=price_min_cents,
            price_max_cents=price_max_cents,
        )
        offers = [
            {
                **offer.model_dump(),
                "links_list": json.loads(offer.links or "[]"),
            }
            for offer in offers
        ]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "offers": offers,
            "q": q or "",
            "categories": categories,
            "category": category or "",
            "days": days_int or "",
            "days_presets": DAYS_PRESETS,
            "price_min": price_min if price_min_cents is not None else "",
            "price_max": price_max if price_max_cents is not None else "",
        },
    )
