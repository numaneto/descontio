#!/usr/bin/env python3
"""Backfill de subcategoria pras ofertas já classificadas antes de
app/categories.py ganhar SUBCATEGORY_KEYWORDS (migração 0007_subcategories).

Só rebaixa uma oferta pra subcategoria quando ela já está classificada
numa categoria-pai (nível 1) e o nome bate com alguma palavra-chave de
subcategoria — nunca mexe em ofertas sem categoria nem reclassifica o
nível 1. Idempotente: rodar de novo não faz nada em ofertas que já têm
`category_id` apontando pra uma subcategoria.
"""
import argparse
import logging

from sqlmodel import select

from app.categories import classify_subcategory_slug
from app.db import get_session
from app.models import Category, Offer

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    with get_session() as session:
        categories = session.exec(select(Category)).all()
        by_id = {item.id: item for item in categories}
        by_slug = {item.slug: item for item in categories}
        # Só categorias de nível 1 (sem parent_id) são candidatas a ganhar
        # uma subcategoria mais específica.
        top_level_ids = {item.id for item in categories if item.parent_id is None}

        updated = 0
        offset = 0
        while True:
            offers = session.exec(
                select(Offer)
                .where(
                    Offer.archived == False,  # noqa: E712
                    Offer.category_id != None,  # noqa: E711
                    Offer.product_name != None,  # noqa: E711
                )
                .order_by(Offer.id)
                .offset(offset)
                .limit(args.batch_size)
            ).all()
            if not offers:
                break
            offset += args.batch_size

            for offer in offers:
                if offer.category_id not in top_level_ids:
                    continue  # já é subcategoria ou categoria desconhecida
                parent = by_id[offer.category_id]
                sub_slug = classify_subcategory_slug(offer.product_name, parent.slug)
                if not sub_slug:
                    continue
                subcategory = by_slug.get(sub_slug)
                if not subcategory:
                    continue
                offer.category_id = subcategory.id
                offer.category = subcategory.name
                session.add(offer)
                updated += 1
            session.commit()

        logger.info("Subcategorizadas %d ofertas", updated)


if __name__ == "__main__":
    main()
