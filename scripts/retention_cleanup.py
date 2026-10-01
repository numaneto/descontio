"""Job de retenção: arquiva ofertas com mais de RETENTION_DAYS dias.

'Arquivar' aqui significa: apaga a imagem física do disco (é o que ocupa
espaço de verdade) e marca `archived=True` no banco, o que faz a oferta
sumir da busca padrão do portal (`app/routes_web.py`). O texto/metadados
NUNCA são apagados — é só um filtro de exibição + limpeza de mídia.

Uso:
    python scripts/retention_cleanup.py [--dry-run]

Pensado pra rodar periodicamente (cron/systemd timer no host, uma vez por
dia é suficiente) via:
    docker compose run --rm web python scripts/retention_cleanup.py
"""
import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import delete, select  # noqa: E402

from app.config import MEDIA_DIR, RETENTION_DAYS  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import Offer, RejectedInput  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run(dry_run: bool = False) -> None:
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    with get_session() as session:
        if not dry_run:
            session.exec(delete(RejectedInput).where(RejectedInput.expires_at < datetime.utcnow()))
            session.commit()

        stmt = select(Offer).where(Offer.archived == False, Offer.posted_at < cutoff)  # noqa: E712
        offers = session.exec(stmt).all()

        if not offers:
            logger.info(
                "Nenhuma oferta com mais de %d dias (cutoff=%s) — nada a arquivar.",
                RETENTION_DAYS,
                cutoff.date(),
            )
            return

        logger.info(
            "%d oferta(s) com mais de %d dias — %s.",
            len(offers),
            RETENTION_DAYS,
            "simulando (--dry-run)" if dry_run else "arquivando",
        )

        freed_bytes = 0
        for offer in offers:
            if offer.image_path:
                image_file = MEDIA_DIR / offer.image_path
                if image_file.exists():
                    freed_bytes += image_file.stat().st_size
                    if not dry_run:
                        image_file.unlink()
                if not dry_run:
                    offer.image_path = None
            if not dry_run:
                offer.archived = True
                session.add(offer)

        if not dry_run:
            session.commit()

        logger.info(
            "Espaço %s: %.1f MB (%d imagens).",
            "liberado" if not dry_run else "a liberar",
            freed_bytes / (1024 * 1024),
            len(offers),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run", action="store_true", help="Só mostra o que seria feito, sem alterar nada."
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
