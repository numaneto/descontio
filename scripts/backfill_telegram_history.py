"""Backfill: varre o histórico recente de cada canal/grupo do Telegram
configurado em config/channels.yaml e ingere as mensagens antigas (rodar
uma vez, ou sempre que quiser popular o portal com posts anteriores ao
início do worker).

Usa a mesma sessão (TELEGRAM_SESSION_STRING) e o mesmo `ingest_post` do
worker em tempo real — é seguro rodar várias vezes, a dedup por
message_id evita duplicar ofertas.

Uso:
    docker compose run --rm web python scripts/backfill_telegram_history.py [--limit N]

    --limit N   Quantas mensagens mais recentes buscar por canal (padrão 50).
"""
import argparse
import asyncio
import logging

from telethon import TelegramClient
from telethon.sessions import StringSession

from app.channels import load_channels
from app.config import TELEGRAM_API_HASH, TELEGRAM_API_ID, TELEGRAM_SESSION_STRING
from app.ingest import ingest_post, save_image_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_channel(client: TelegramClient, channel: dict, limit: int) -> tuple[int, int]:
    chat_id = channel["chat_id"]
    label = channel.get("label", chat_id)
    ingested = 0
    skipped = 0

    try:
        entity = await client.get_entity(chat_id)
    except Exception:  # noqa: BLE001
        logger.exception("Não consegui resolver o canal %s (%s) — pulando", chat_id, label)
        return 0, 0

    async for message in client.iter_messages(entity, limit=limit):
        text = message.raw_text or ""
        if not text and not message.photo:
            continue  # mensagem sem texto e sem foto não vira oferta

        message_id = str(message.id)
        image_path = None
        if message.photo:
            try:
                image_bytes = await message.download_media(bytes)
                if image_bytes:
                    image_path = save_image_bytes("telegram", message_id, image_bytes)
            except Exception:  # noqa: BLE001
                logger.exception("Falha ao baixar foto da mensagem %s/%s", chat_id, message_id)

        engagement = 0
        if message.reactions:
            engagement = sum(r.count for r in message.reactions.results)

        offer = ingest_post(
            platform="telegram",
            group_id=chat_id,
            group_label=label,
            message_id=message_id,
            text=text,
            image_path=image_path,
            posted_at=message.date,
            category_default=channel.get("category"),
            engagement_score=engagement,
        )
        if offer is not None:
            ingested += 1
        else:
            skipped += 1

    return ingested, skipped


async def main(limit: int) -> None:
    if not (TELEGRAM_API_ID and TELEGRAM_API_HASH and TELEGRAM_SESSION_STRING):
        raise SystemExit(
            "TELEGRAM_API_ID/TELEGRAM_API_HASH/TELEGRAM_SESSION_STRING não configurados. "
            "Rode scripts/telegram_login.py primeiro."
        )

    channels = [c for c in load_channels() if c.get("platform") == "telegram"]
    if not channels:
        logger.warning("Nenhum canal Telegram configurado em config/channels.yaml.")
        return

    client = TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH
    )
    await client.start()
    logger.info("Conectado. Iniciando backfill de %d canais (limite=%d cada).", len(channels), limit)

    total_ingested = 0
    total_skipped = 0
    for channel in channels:
        ingested, skipped = await backfill_channel(client, channel, limit)
        total_ingested += ingested
        total_skipped += skipped
        logger.info(
            "%s: %d ofertas novas, %d já existiam", channel.get("label", channel["chat_id"]), ingested, skipped
        )

    logger.info(
        "Backfill concluído: %d ofertas novas no total, %d já existiam.", total_ingested, total_skipped
    )
    await client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50, help="Mensagens recentes por canal (padrão 50)")
    args = parser.parse_args()
    asyncio.run(main(args.limit))
