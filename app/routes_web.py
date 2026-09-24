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


@router.get("/")
def index(
    request: Request,
    q: str | None = Query(default=None, description="Busca por palavra-chave"),
    source_group: str | None = Query(default=None),
    days: int | None = Query(default=None, description="Só ofertas dos últimos N dias"),
):
    no_filters = not q and not source_group and not days

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
            "days": days or "",
        },
    )
