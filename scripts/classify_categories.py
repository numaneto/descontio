#!/usr/bin/env python3
"""Classifica ofertas existentes usando a taxonomia controlada."""
import argparse
import json
import logging

import httpx
from sqlmodel import select

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_ENABLED, LLM_MODEL
from app.db import get_session
from app.models import Category, Offer
from app.parsers.llm_parser import ALLOWED_CATEGORIES, _parse_json, _record_usage

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROMPT = """Classifique cada produto em exatamente uma categoria permitida.
Não invente categorias. Responda somente JSON no formato:
{{"items":[{{"id":123,"category_slug":"informatica"}}]}}

Categorias: {categories}
Produtos:
{products}
"""


def classify_batch(offers: list[Offer]) -> dict[int, str] | None:
    payload = None
    response = None
    try:
        response = httpx.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": "Bearer " + LLM_API_KEY,
                "User-Agent": "curl/8.0",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": PROMPT.format(
                            categories=", ".join(ALLOWED_CATEGORIES),
                            products=json.dumps(
                                [{"id": item.id, "name": item.product_name} for item in offers],
                                ensure_ascii=False,
                            ),
                        ),
                    }
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        data = _parse_json(payload["choices"][0]["message"]["content"])
        _record_usage(payload, success=True, operation="category_classifier")
    except Exception:  # noqa: BLE001
        if payload is not None:
            _record_usage(payload, success=False, operation="category_classifier")
        logger.exception(
            "Falha na classificação: %s",
            response.text[:500] if response is not None else "",
        )
        return None

    return {
        int(item["id"]): item["category_slug"]
        for item in data.get("items", [])
        if item.get("category_slug") in ALLOWED_CATEGORIES
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not LLM_ENABLED or not LLM_API_KEY:
        raise SystemExit("LLM_ENABLED/LLM_API_KEY não configurados")

    processed = 0
    while not args.limit or processed < args.limit:
        remaining = args.batch_size
        if args.limit:
            remaining = min(remaining, args.limit - processed)
        with get_session() as session:
            offers = session.exec(
                select(Offer)
                .where(
                    Offer.archived == False,  # noqa: E712
                    Offer.category_id == None,  # noqa: E711
                    Offer.product_name != None,  # noqa: E711
                )
                .order_by(Offer.id)
                .limit(remaining)
            ).all()
            if not offers:
                break

            result = classify_batch(offers)
            if result is None:
                raise SystemExit("Classificação interrompida após falha do provedor")
            categories = {
                item.slug: item
                for item in session.exec(
                    select(Category).where(Category.slug.in_(set(result.values())))
                ).all()
            }
            for offer in offers:
                slug = result.get(offer.id, "outros")
                category = categories.get(slug)
                if category:
                    offer.category_id = category.id
                    offer.category = category.name
                    session.add(offer)
            session.commit()
            processed += len(offers)
            logger.info("Classificadas %d ofertas", processed)

    logger.info("Concluído: %d ofertas processadas", processed)


if __name__ == "__main__":
    main()
