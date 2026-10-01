"""API pública de leitura (JSON) do descont.io.

Só leitura — reusa a mesma lógica de filtro do portal HTML
(`app/offers_query.py`) pra manter os dois sempre consistentes. Pensada
como o embrião de uma "API de preços" maior: hoje devolve o que já existe
(Offer), no futuro deve incluir Categoria/Produto (ver
docs/07-descontio.md em home-nw-docs pro desenho completo).
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db import get_session
from app.models import Offer
from app.offers_query import (
    API_DEFAULT_DAYS,
    MAX_DAYS,
    RESULT_LIMIT,
    display_source_label,
    load_hidden_channel_keys,
    parse_days,
    parse_price,
    query_offers,
)
from app.rate_limit import RateLimited

router = APIRouter(prefix="/api/v1", tags=["public-api"])

# Teto de itens por página pra não deixar um client pedir o banco inteiro
# de uma vez só (o portal usa RESULT_LIMIT=200 como página "grande").
MAX_LIMIT = RESULT_LIMIT


class OfferOut(BaseModel):
    id: int
    product_name: str | None
    price: float | None
    price_original: float | None
    coupon_code: str | None
    links: list[str]
    image_url: str | None
    category: str | None
    source: str
    posted_at: datetime

    class Config:
        from_attributes = True


def _to_offer_out(offer: Offer, hidden_keys: set[tuple[str, str]]) -> OfferOut:
    try:
        links = json.loads(offer.links or "[]")
    except json.JSONDecodeError:
        links = []
    posted_at = offer.posted_at
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    return OfferOut(
        id=offer.id,
        product_name=offer.product_name,
        price=offer.price,
        price_original=offer.price_original,
        coupon_code=offer.coupon_code,
        links=links,
        image_url=f"/media/{offer.image_path}" if offer.image_path else None,
        category=offer.category,
        # Nome do canal/grupo de origem — oculto (rótulo genérico) quando
        # o canal tem hide_brand=True na admin UI (/admin/channels).
        source=display_source_label(offer, hidden_keys),
        posted_at=posted_at,
    )


class OfferListOut(BaseModel):
    count: int
    results: list[OfferOut]


@router.get("/offers", response_model=OfferListOut, dependencies=[RateLimited])
def list_offers(
    q: str | None = Query(default=None, description="Busca por palavra-chave (múltiplos termos, sem acento/caixa)"),
    days: str | None = Query(
        default=None,
        description=f"Só ofertas dos últimos N dias (1-{MAX_DAYS}). Default {API_DEFAULT_DAYS} se omitido.",
    ),
    price_min: str | None = Query(default=None, description="Preço mínimo (R$)"),
    price_max: str | None = Query(default=None, description="Preço máximo (R$)"),
    limit: int = Query(default=60, ge=1, le=MAX_LIMIT, description=f"Máximo de itens retornados (até {MAX_LIMIT})"),
) -> OfferListOut:
    # Sem `days` explícito, a API assume uma janela curta (ofertas mudam
    # rápido) em vez de devolver o histórico inteiro — ver offers_query.py.
    days_int = parse_days(days) if days is not None else API_DEFAULT_DAYS
    price_min_val = parse_price(price_min)
    price_max_val = parse_price(price_max)
    if price_min_val is not None and price_max_val is not None and price_min_val > price_max_val:
        price_min_val = price_max_val = None

    with get_session() as session:
        offers = query_offers(
            session,
            q=q,
            days_int=days_int,
            price_min=price_min_val,
            price_max=price_max_val,
            limit=limit,
        )
        hidden_keys = load_hidden_channel_keys(session)
    return OfferListOut(count=len(offers), results=[_to_offer_out(o, hidden_keys) for o in offers])


@router.get("/offers/{offer_id}", response_model=OfferOut, dependencies=[RateLimited])
def get_offer(offer_id: int) -> OfferOut:
    with get_session() as session:
        offer = session.get(Offer, offer_id)
        if offer is None or offer.archived:
            raise HTTPException(status_code=404, detail="oferta nao encontrada")
        hidden_keys = load_hidden_channel_keys(session)
        return _to_offer_out(offer, hidden_keys)
