"""Polling do Telegram: substitui o worker de conexão viva
(workers/telegram_worker.py, client.on(events.NewMessage())) por ciclos
curtos e independentes.

Motivo da troca (ver STATUS.md, incidente 2026-09-30): o listener de
eventos do Telethon fica com uma conexão aberta por dias; reconexões
automáticas de rede disparam `get_difference` internamente e, num bug
conhecido, travam o dispatch de `NewMessage` **sem gerar nenhum erro nos
logs** — o worker aparecia "conectado, escutando 7/7 canais" por 9h+ sem
ingerir nada. Com polling, cada execução é uma conexão nova e curta: se uma
rodada falhar, a próxima (cron, alguns minutos depois) simplesmente tenta
de novo a partir do último estado salvo — sem ponto único de falha
silenciosa.

Cada canal tem seu próprio `last_message_id` (tabela `channel_poll_state`),
então só busca mensagens novas (`iter_messages(min_id=...)`) — ao contrário
do backfill (que sempre varre as últimas N mensagens e descarta duplicatas
via dedup), aqui não rebaixamos imagem de posts já vistos.

Uso (via cron, ver docs/07-hub-offers.md):
    docker compose run --rm web python scripts/poll_telegram.py
"""
import asyncio
import logging
from datetime import datetime

from sqlmodel import select
from telethon import TelegramClient
from telethon.sessions import StringSession

from app.channels import load_channels
from app.config import TELEGRAM_API_HASH, TELEGRAM_API_ID, TELEGRAM_SESSION_STRING
from app.db import get_session, init_db
from app.ingest import ingest_post, save_image_bytes
from app.models import ChannelPollState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Primeira execução de um canal (sem estado salvo ainda): ingere só as
# últimas N mensagens em vez de todo o histórico (que já foi coberto pelo
# backfill manual) — evita reprocessar tudo de novo num canal novo/reset.
BOOTSTRAP_LIMIT = 20
# Teto de segurança por ciclo — se por algum motivo (ex.: cron parado por
# horas) o gap crescer muito, não tenta puxar histórico infinito de uma vez.
MAX_PER_CYCLE = 300


def _get_or_create_state(session, platform: str, chat_id: str) -> ChannelPollState:
    state = session.get(ChannelPollState, (platform, chat_id))
    if state is None:
        state = ChannelPollState(platform=platform, chat_id=chat_id, last_message_id=0)
        session.add(state)
        session.commit()
        session.refresh(state)
    return state


async def poll_channel(client: TelegramClient, channel: dict) -> tuple[int, int]:
    chat_id = channel["chat_id"]
    label = channel.get("label", chat_id)
    ingested = 0
    seen = 0

    with get_session() as session:
        state = _get_or_create_state(session, "telegram", chat_id)
        last_id = state.last_message_id

    try:
        entity = await client.get_entity(chat_id)
    except Exception:  # noqa: BLE001
        logger.exception("Não consegui resolver o canal %s (%s) — pulando", chat_id, label)
        return 0, 0

    kwargs = {"limit": MAX_PER_CYCLE}
    if last_id:
        kwargs["min_id"] = last_id
    else:
        # Bootstrap: primeira vez que este canal é "polado" — só as últimas
        # BOOTSTRAP_LIMIT mensagens, não o histórico inteiro.
        kwargs["limit"] = BOOTSTRAP_LIMIT

    max_id_seen = last_id
    async for message in client.iter_messages(entity, **kwargs):
        seen += 1
        max_id_seen = max(max_id_seen, message.id)

        text = message.raw_text or ""
        if not text and not message.photo:
            continue

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

    with get_session() as session:
        state = _get_or_create_state(session, "telegram", chat_id)
        state.last_message_id = max(state.last_message_id, max_id_seen)
        state.last_polled_at = datetime.utcnow()
        session.add(state)
        session.commit()

    return ingested, seen


async def main() -> None:
    if not (TELEGRAM_API_ID and TELEGRAM_API_HASH and TELEGRAM_SESSION_STRING):
        raise SystemExit(
            "TELEGRAM_API_ID/TELEGRAM_API_HASH/TELEGRAM_SESSION_STRING não configurados. "
            "Rode scripts/telegram_login.py primeiro."
        )

    init_db()  # garante que channel_poll_state existe, mesmo rodando isolado

    channels = [c for c in load_channels() if c.get("platform") == "telegram"]
    if not channels:
        logger.warning("Nenhum canal Telegram configurado em config/channels.yaml.")
        return

    client = TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH
    )
    await client.start()
    logger.info("Conectado. Polling de %d canais.", len(channels))

    total_ingested = 0
    for channel in channels:
        ingested, seen = await poll_channel(client, channel)
        total_ingested += ingested
        if seen:
            logger.info(
                "%s: %d mensagens novas verificadas, %d ofertas ingeridas",
                channel.get("label", channel["chat_id"]),
                seen,
                ingested,
            )

    logger.info("Ciclo de polling concluído: %d ofertas novas no total.", total_ingested)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
