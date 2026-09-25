"""Reprocessa o preço (e nome do produto) de ofertas já ingeridas, usando a
versão atual do parser de regex sobre o `raw_text` já salvo.

Uso pontual depois de um fix no parser (ex.: bug do cupom sendo confundido
com o preço final, corrigido em 2026-09-25) — sem isso, ofertas antigas
ficariam com o valor errado gravado pra sempre, já que a ingestão só roda
o parser uma vez (na hora do post).

    docker compose run --rm web python scripts/reparse_prices.py [--dry-run]
"""
import argparse
import logging

from sqlmodel import select

from app.db import get_session
from app.models import Offer
from app.parsers.pipeline import extract

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Só mostra o que mudaria, sem salvar.")
    args = parser.parse_args()

    changed = 0
    total = 0
    with get_session() as session:
        offers = session.exec(select(Offer)).all()
        for offer in offers:
            total += 1
            parsed, method = extract(offer.raw_text or "")
            # Só reaplica preço/nome — não mexe em cupom/links/categoria,
            # que já foram tratados/curados manualmente em alguns casos.
            if parsed.price != offer.price or parsed.price_original != offer.price_original:
                logger.info(
                    "Oferta %s (%s): preço %s -> %s (original %s -> %s)",
                    offer.id,
                    (offer.product_name or "")[:60],
                    offer.price,
                    parsed.price,
                    offer.price_original,
                    parsed.price_original,
                )
                changed += 1
                if not args.dry_run:
                    offer.price = parsed.price
                    offer.price_original = parsed.price_original
                    offer.parse_method = method
                    offer.parse_confidence = parsed.confidence
                    session.add(offer)
        if not args.dry_run:
            session.commit()

    logger.info(
        "Concluído: %s/%s ofertas com preço recalculado%s.",
        changed,
        total,
        " (dry-run, nada foi salvo)" if args.dry_run else "",
    )


if __name__ == "__main__":
    main()
