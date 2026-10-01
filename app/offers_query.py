"""Lógica de filtro de ofertas compartilhada entre o portal HTML
(routes_web.py) e a API pública (routes_api_public.py) — um único lugar
pra manter days/price/busca textual consistentes nos dois.
"""
import unicodedata
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.models import Category, Offer
from app.money import parse_brl_to_cents

# Presets exibidos no dropdown do filtro de tempo (portal) — além destes,
# qualquer valor inteiro entre 1 e MAX_DAYS também é aceito (ex.: um link
# compartilhado com "?days=10"), só os presets é que aparecem na UI.
# Limitado a 7 dias porque é também o teto de RETENTION_DAYS (app/config.py).
DAYS_PRESETS = (1, 3, 7)
MAX_DAYS = 7

# Default de `days` quando a API pública é chamada sem o parâmetro — mais
# curto que o MAX_DAYS do portal porque consumidores de API tendem a querer
# "o que há de mais recente" por padrão (ver app/routes_api_public.py).
API_DEFAULT_DAYS = 7

DEFAULT_PER_CHANNEL = 10
# Limite de resultados retornados numa busca filtrada — a filtragem por
# texto roda em Python (ver `matches_query`), então buscamos um pouco além
# do limite final de exibição pra não perder itens relevantes que a busca
# textual descarte depois do corte do SQL.
SQL_PREFETCH_LIMIT = 5000
RESULT_LIMIT = 200


def normalize(value: str) -> str:
    """Remove acentos e normaliza pra minúsculo, pra busca não depender de
    o usuário digitar exatamente os mesmos acentos do texto original (ex:
    buscar "geladeira" deve achar "Geladeira" e "GELADEIRA" igual)."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_accents.lower()


def matches_query(offer: Offer, terms: list[str]) -> bool:
    """Busca somente no nome normalizado publicado.

    O texto bruto é privado e contém propaganda, nomes de grupos e listas de
    produtos não relacionados, que geravam falsos positivos.
    """
    haystack = normalize(offer.product_name or "")
    return all(term in haystack for term in terms)


def parse_days(days: str | None) -> int | None:
    """`days` aceita qualquer inteiro positivo dentro de um limite sensato
    (1-365) — fora disso (não numérico, negativo, absurdamente grande) é
    tratado como "sem filtro de data", em vez de estourar 422 ou aplicar
    um corte arbitrário."""
    if not days:
        return None
    try:
        candidate = int(days)
    except ValueError:
        return None
    if 1 <= candidate <= MAX_DAYS:
        return candidate
    return None


def parse_price(value: str | float | None) -> int | None:
    return parse_brl_to_cents(value)


def query_offers(
    session: Session,
    *,
    q: str | None = None,
    category_slug: str | None = None,
    days_int: int | None = None,
    price_min_cents: int | None = None,
    price_max_cents: int | None = None,
    limit: int = RESULT_LIMIT,
) -> list[Offer]:
    """Filtro central (sem o caso especial de "home sem filtro nenhum",
    que é só do portal — ver routes_web.py)."""
    stmt = select(Offer).where(Offer.archived == False).order_by(Offer.posted_at.desc())  # noqa: E712

    if category_slug:
        category_id = session.exec(
            select(Category.id).where(Category.slug == category_slug)
        ).first()
        if category_id is None:
            return []
        stmt = stmt.where(Offer.category_id == category_id)
    if days_int:
        cutoff = datetime.utcnow() - timedelta(days=days_int)
        stmt = stmt.where(Offer.posted_at >= cutoff)
    if price_min_cents is not None:
        stmt = stmt.where(Offer.price_cents >= price_min_cents)
    if price_max_cents is not None:
        stmt = stmt.where(Offer.price_cents <= price_max_cents)

    if q:
        # Pré-filtro grosseiro no SQL (o texto ainda é filtrado fino em
        # Python, sem acento, multi-termo) — busca um pouco além do limite
        # final pra não perder itens que o corte do SQL descartaria antes
        # do filtro textual rodar.
        terms = [t for t in normalize(q).split() if t]
        candidates = session.exec(stmt.limit(SQL_PREFETCH_LIMIT)).all()
        return [o for o in candidates if matches_query(o, terms)][:limit]

    return session.exec(stmt.limit(limit)).all()
