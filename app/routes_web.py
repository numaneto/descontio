"""Rotas do portal web (HTML server-rendered, feed de ofertas com filtros)."""
import json
import unicodedata
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from app.channels import load_channels
from app.db import get_session
from app.models import Offer

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DEFAULT_PER_CHANNEL = 10
# Presets exibidos no dropdown do filtro de tempo — além destes, qualquer
# valor inteiro entre 1 e MAX_DAYS também é aceito (ex.: um link
# compartilhado com "?days=45"), só os presets é que aparecem na UI.
DAYS_PRESETS = (1, 3, 7, 15, 30, 90)
MAX_DAYS = 365
# Limite de resultados retornados numa busca filtrada — a filtragem por
# texto roda em Python (ver `_matches_query`), então buscamos um pouco além
# do limite final de exibição pra não perder itens relevantes que a busca
# textual descarte depois do corte do SQL.
SQL_PREFETCH_LIMIT = 2000
RESULT_LIMIT = 200


def _normalize(value: str) -> str:
    """Remove acentos e normaliza pra minúsculo, pra busca não depender de
    o usuário digitar exatamente os mesmos acentos do texto original (ex:
    buscar "geladeira" deve achar "Geladeira" e "GELADEIRA" igual)."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_accents.lower()


def _matches_query(offer: Offer, terms: list[str]) -> bool:
    """Busca robusta: cada termo (palavra) da query precisa aparecer em
    algum lugar do nome do produto ou do texto bruto, em qualquer ordem —
    ao contrário de um LIKE simples com a frase inteira, "rtx 5060 16gb"
    acha um post que tenha essas 3 palavras em qualquer posição/ordem, e
    não depende de acento/caixa."""
    haystack = _normalize(f"{offer.product_name or ''} {offer.raw_text or ''}")
    return all(term in haystack for term in terms)


@router.get("/")
def index(
    request: Request,
    q: str | None = Query(default=None, description="Busca por palavra-chave (aceita múltiplos termos)"),
    source_group: str | None = Query(default=None),
    days: str | None = Query(default=None, description=f"Só ofertas dos últimos N dias (1-{MAX_DAYS})"),
):
    # `days` aceita qualquer inteiro positivo dentro de um limite sensato
    # (1-365) — fora disso (não numérico, negativo, absurdamente grande) é
    # tratado como "sem filtro de data", em vez de estourar 422 ou aplicar
    # um corte arbitrário.
    days_int: int | None = None
    if days:
        try:
            candidate = int(days)
        except ValueError:
            candidate = None
        if candidate is not None and 1 <= candidate <= MAX_DAYS:
            days_int = candidate

    no_filters = not q and not source_group and not days_int

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
            stmt = select(Offer).where(Offer.archived == False).order_by(Offer.posted_at.desc())  # noqa: E712

            if source_group:
                stmt = stmt.where(Offer.source_group == source_group)
            if days_int:
                cutoff = datetime.utcnow() - timedelta(days=days_int)
                stmt = stmt.where(Offer.posted_at >= cutoff)

            if q:
                # Pré-filtro grosseiro no SQL (LIKE pelo texto inteiro da
                # query, se bater já ajuda a podar o prefetch) + filtro fino
                # em Python (multi-termo, sem acento) — o corte final some
                # RESULT_LIMIT só depois da busca textual, senão o LIKE
                # sozinho poderia enviesar quais itens chegam pro filtro
                # fino.
                terms = [t for t in _normalize(q).split() if t]
                candidates = session.exec(stmt.limit(SQL_PREFETCH_LIMIT)).all()
                offers = [o for o in candidates if _matches_query(o, terms)][:RESULT_LIMIT]
            else:
                offers = session.exec(stmt.limit(RESULT_LIMIT)).all()

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
            "days": days_int or "",
            "days_presets": DAYS_PRESETS,
        },
    )
