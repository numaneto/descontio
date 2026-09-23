"""Lógica compartilhada de ingestão: recebe um post bruto (de qualquer
plataforma), roda o parser híbrido, dedup e persiste no banco."""
import json
import logging
from datetime import datetime
from pathlib import Path

from sqlmodel import select

from app.config import MEDIA_DIR
from app.db import get_session
from app.models import Offer
from app.parsers.pipeline import extract

logger = logging.getLogger(__name__)


def save_image_bytes(platform: str, message_id: str, content: bytes, ext: str = "jpg") -> str:
    """Salva a imagem em disco e devolve o caminho relativo (pra servir via /media)."""
    subdir = MEDIA_DIR / platform
    subdir.mkdir(parents=True, exist_ok=True)
    filename = f"{message_id}.{ext}"
    path = subdir / filename
    path.write_bytes(content)
    return f"{platform}/{filename}"


def ingest_post(
    *,
    platform: str,
    group_id: str,
    group_label: str,
    message_id: str,
    text: str,
    image_path: str | None = None,
    posted_at: datetime | None = None,
    category_default: str | None = None,
    engagement_score: int = 0,
) -> Offer | None:
    """Ingere um post bruto. Retorna o Offer criado, ou None se já existia
    (idempotente por plataforma+grupo+message_id)."""
    with get_session() as session:
        existing = session.exec(
            select(Offer).where(
                Offer.source_platform == platform,
                Offer.source_group == group_id,
                Offer.source_message_id == message_id,
            )
        ).first()
        if existing:
            logger.info("Post %s/%s/%s já ingerido, ignorando", platform, group_id, message_id)
            return None

        parsed, method = extract(text)

        offer = Offer(
            source_platform=platform,
            source_group=group_id,
            source_label=group_label,
            source_message_id=message_id,
            raw_text=text,
            image_path=image_path,
            product_name=parsed.product_name,
            price=parsed.price,
            price_original=parsed.price_original,
            coupon_code=parsed.coupon_code,
            links=json.dumps(parsed.links),
            category=category_default,
            parse_method=method,
            parse_confidence=parsed.confidence,
            engagement_score=engagement_score,
            posted_at=posted_at or datetime.utcnow(),
        )
        session.add(offer)
        session.commit()
        session.refresh(offer)
        logger.info(
            "Post ingerido: %s/%s (metodo=%s, confianca=%.2f)",
            platform,
            message_id,
            method,
            parsed.confidence,
        )
        return offer
