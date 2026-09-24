"""Rotas do portal web (HTML server-rendered, feed de ofertas com filtros)."""
import json
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
ALLOWED_DAYS = {1, 7, 30}


def _escape_like(value: str) -> str:
    """Escapa os curingas do LIKE (`%`, `_`) pra que uma busca por esses
    caracteres literais não vire um match-all/match-parcial indesejado."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/")
def index(
    request: Request,
    q: str | None = Query(default=None, description="Busca por palavra-chave"),
    source_group: str | None = Query(default=None),
    days: str | None = Query(default=None, description="Só ofertas dos últimos N dias (1, 7 ou 30)"),
):
    # `days` só aceita os valores conhecidos do filtro (1/7/30) — qualquer
    # outra coisa (não numérico, negativo, fora da whitelist) é tratada como
    # "sem filtro de data", em vez de estourar 422 ou aplicar um corte
    # arbitrário.
    days_int: int | None = None
    if days:
        try:
            candidate = int(days)
        except ValueError:
            candidate = None
        if candidate in ALLOWED_DAYS:
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

            if q:
                like = f"%{_escape_like(q)}%"
                stmt = stmt.where(
                    (Offer.product_name.like(like, escape="\\"))
                    | (Offer.raw_text.like(like, escape="\\"))
                )
            if source_group:
                stmt = stmt.where(Offer.source_group == source_group)
            if days_int:
                cutoff = datetime.utcnow() - timedelta(days=days_int)
                stmt = stmt.where(Offer.posted_at >= cutoff)

            offers = session.exec(stmt.limit(200)).all()

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
        },
    )
