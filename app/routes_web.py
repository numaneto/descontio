"""Rotas do portal web (HTML server-rendered, feed de ofertas com filtros)."""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from app.channels import load_channels
from app.db import get_session
from app.models import Offer
from app.offers_query import (
    DAYS_PRESETS,
    DEFAULT_PER_CHANNEL,
    display_source_label,
    load_hidden_channel_keys,
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


@router.get("/")
def index(
    request: Request,
    q: str | None = Query(default=None, description="Busca por palavra-chave (aceita múltiplos termos)"),
    source_group: str | None = Query(default=None),
    days: str | None = Query(default=None, description="Só ofertas dos últimos N dias (1-365)"),
    price_min: str | None = Query(default=None, description="Preço mínimo (R$)"),
    price_max: str | None = Query(default=None, description="Preço máximo (R$)"),
):
    days_int = parse_days(days)
    price_min_val = parse_price(price_min)
    price_max_val = parse_price(price_max)
    # Preço mínimo maior que o máximo não faz sentido — ignora os dois em
    # vez de devolver sempre um resultado vazio sem explicação nenhuma.
    if price_min_val is not None and price_max_val is not None and price_min_val > price_max_val:
        price_min_val = price_max_val = None

    no_filters = not q and not source_group and not days_int and price_min_val is None and price_max_val is None

    with get_session() as session:
        if no_filters:
            # Sem filtro nenhum: traz as últimas N ofertas de CADA canal
            # registrado (config/channels.yaml), não só as N mais recentes
            # globais — assim um canal que posta pouco não some da home.
            offers = []
            for channel in load_channels():
                chat_id = channel.get("chat_id")
                stmt = (
                    select(Offer)
                    .where(Offer.archived == False, Offer.source_group == chat_id)  # noqa: E712
                    .order_by(Offer.posted_at.desc())
                    .limit(DEFAULT_PER_CHANNEL)
                )
                offers.extend(session.exec(stmt).all())
            offers.sort(key=lambda o: o.posted_at, reverse=True)
        else:
            offers = query_offers(
                session,
                q=q,
                source_group=source_group,
                days_int=days_int,
                price_min=price_min_val,
                price_max=price_max_val,
            )

        groups = session.exec(
            select(Offer.source_group, Offer.source_label).distinct()
        ).all()
        known_group_ids = {g[0] for g in groups}
        # Inclui no filtro também canais registrados que ainda não têm
        # nenhuma oferta ingerida (ex.: logo após adicionar um canal novo).
        for channel in load_channels():
            chat_id = channel.get("chat_id")
            if chat_id not in known_group_ids:
                groups.append((chat_id, channel.get("label", chat_id)))
                known_group_ids.add(chat_id)

        # SQLModel não aceita atributos fora do schema declarado — construímos
        # um dict simples por oferta pra passar os links já decodificados ao
        # template, sem mexer no modelo. `source_label` é sobrescrito pelo
        # rótulo genérico quando o canal tem hide_brand=True (admin UI).
        hidden_keys = load_hidden_channel_keys(session)
        offers = [
            {
                **offer.model_dump(),
                "links_list": json.loads(offer.links or "[]"),
                "source_label": display_source_label(offer, hidden_keys),
            }
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
            "days": days_int or "",
            "days_presets": DAYS_PRESETS,
            "price_min": price_min if price_min_val is not None else "",
            "price_max": price_max if price_max_val is not None else "",
        },
    )
