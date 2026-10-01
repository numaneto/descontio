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
from sqlmodel import select

from app.db import get_session
from app.models import Category, Offer
from app.offers_query import (
    API_DEFAULT_DAYS,
    MAX_DAYS,
    RESULT_LIMIT,
    SORT_OPTIONS,
    parse_days,
    parse_price,
    parse_sort,
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
    price_cents: int | None
    price_original_cents: int | None
    currency: str = "BRL"
    coupon_code: str | None
    links: list[str]
    image_url: str | None
    category: str | None
    category_slug: str | None
    posted_at: datetime

    class Config:
        from_attributes = True


def _to_offer_out(offer: Offer, category: Category | None = None) -> OfferOut:
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
        price_cents=offer.price_cents,
        price_original_cents=offer.price_original_cents,
        coupon_code=offer.coupon_code,
        links=links,
        image_url=f"/media/{offer.image_path}" if offer.image_path else None,
        category=category.name if category else offer.category,
        category_slug=category.slug if category else None,
        posted_at=posted_at,
    )


class OfferListOut(BaseModel):
    count: int
    results: list[OfferOut]


@router.get("/offers", response_model=OfferListOut, dependencies=[RateLimited])
def list_offers(
    q: str | None = Query(default=None, description="Busca por palavra-chave (múltiplos termos, sem acento/caixa)"),
    category: str | None = Query(default=None, description="Slug da categoria"),
    days: str | None = Query(
        default=None,
        description=f"Só ofertas dos últimos N dias (1-{MAX_DAYS}). Default {API_DEFAULT_DAYS} se omitido.",
    ),
    price_min: str | None = Query(default=None, description="Preço mínimo (R$)"),
    price_max: str | None = Query(default=None, description="Preço máximo (R$)"),
    price_min_cents: int | None = Query(default=None, ge=0, description="Preço mínimo em centavos (preferencial)"),
    price_max_cents: int | None = Query(default=None, ge=0, description="Preço máximo em centavos (preferencial)"),
    sort: str | None = Query(
        default=None,
        description=f"Ordenação: {', '.join(SORT_OPTIONS)} (default recent).",
    ),
    limit: int = Query(default=60, ge=1, le=MAX_LIMIT, description=f"Máximo de itens retornados (até {MAX_LIMIT})"),
) -> OfferListOut:
    # Sem `days` explícito, a API assume uma janela curta (ofertas mudam
    # rápido) em vez de devolver o histórico inteiro — ver offers_query.py.
    days_int = parse_days(days) if days is not None else API_DEFAULT_DAYS
    minimum_cents = price_min_cents if price_min_cents is not None else parse_price(price_min)
    maximum_cents = price_max_cents if price_max_cents is not None else parse_price(price_max)
    if minimum_cents is not None and maximum_cents is not None and minimum_cents > maximum_cents:
        minimum_cents = maximum_cents = None

    with get_session() as session:
        offers = query_offers(
            session,
            q=q,
            category_slug=category,
            days_int=days_int,
            price_min_cents=minimum_cents,
            price_max_cents=maximum_cents,
            sort=parse_sort(sort),
            limit=limit,
        )
        category_ids = {offer.category_id for offer in offers if offer.category_id is not None}
        categories = (
            session.exec(select(Category).where(Category.id.in_(category_ids))).all()
            if category_ids
            else []
        )
        category_by_id = {item.id: item for item in categories}
        results = [_to_offer_out(offer, category_by_id.get(offer.category_id)) for offer in offers]
    return OfferListOut(count=len(results), results=results)


@router.get("/offers/{offer_id}", response_model=OfferOut, dependencies=[RateLimited])
def get_offer(offer_id: int) -> OfferOut:
    with get_session() as session:
        offer = session.get(Offer, offer_id)
        if offer is None or offer.archived:
            raise HTTPException(status_code=404, detail="oferta nao encontrada")
        category = session.get(Category, offer.category_id) if offer.category_id else None
        return _to_offer_out(offer, category)
