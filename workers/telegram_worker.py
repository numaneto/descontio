"""Worker de longa duração: conecta no Telegram como user-client (Telethon,
usando a conta pessoal) e ingere cada nova mensagem dos grupos/canais
listados em config/channels.yaml.

Precisa de TELEGRAM_API_ID/TELEGRAM_API_HASH/TELEGRAM_SESSION_STRING no
.env — gere a sessão uma vez com scripts/telegram_login.py.
"""
import asyncio
import logging

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from app.channels import find_channel, load_channels
from app.config import TELEGRAM_API_HASH, TELEGRAM_API_ID, TELEGRAM_SESSION_STRING
from app.ingest import ingest_post, save_image_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _telegram_chat_ids() -> list[str]:
    return [c["chat_id"] for c in load_channels() if c.get("platform") == "telegram"]


async def main() -> None:
    if not (TELEGRAM_API_ID and TELEGRAM_API_HASH and TELEGRAM_SESSION_STRING):
        raise SystemExit(
            "TELEGRAM_API_ID/TELEGRAM_API_HASH/TELEGRAM_SESSION_STRING não configurados. "
            "Rode scripts/telegram_login.py primeiro."
        )

    client = TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH
    )

    chat_ids = _telegram_chat_ids()
    if not chat_ids:
        logger.warning(
            "config/channels.yaml não tem nenhum canal Telegram configurado — "
            "o worker vai conectar mas não vai processar nada."
        )

    await client.start()

    # NAO chamar catch_up() aqui: descobrimos que catch_up() deixa o cliente
    # num estado onde novos eventos NewMessage param de ser entregues (bug
    # documentado do Telethon - catch_up()/get_difference "consome" o estado
    # de atualizacoes e o loop de eventos normal nunca mais dispara, mesmo
    # sem erro no log). Sintoma observado: worker ficava "conectado" e sem
    # erros, mas 0 eventos chegavam por 24h+ (nem no handler de debug sem
    # filtro nenhum) - ver STATUS.md 2026-09-30. Corrigido removendo essa
    # chamada e garantindo o recebimento de updates explicitamente abaixo.
    await client.set_receive_updates(True)

    # IMPORTANTE: resolve cada canal para uma entidade real (chamada de rede)
    # ANTES de registrar o handler. O filtro `chats=` do Telethon casa updates
    # recebidos (que trazem só o ID interno do peer) contra o cache de
    # entidades do cliente — se o username nunca foi resolvido nesta sessão
    # (ex.: logo após um restart do container), o filtro simplesmente nunca
    # bate e a mensagem é descartada em silêncio, sem erro no log. Resolver
    # explicitamente aqui popula o cache e corrige isso (bug real observado:
    # worker ficava "conectado" e sem erros, mas nada era ingerido desde o
    # último restart — ver STATUS.md 2026-09-30).
    resolved_chats = []
    for cid in chat_ids:
        try:
            entity = await client.get_entity(cid)
            resolved_chats.append(entity)
        except Exception:  # noqa: BLE001
            logger.exception("Não consegui resolver o canal %s, ficará sem listener", cid)

    @client.on(events.NewMessage())
    async def _debug_any(event) -> None:
        chat = await event.get_chat()
        logger.info("DEBUG raw event de chat_id=%s username=%s", event.chat_id, getattr(chat, 'username', None))

    @client.on(events.NewMessage(chats=resolved_chats or None))
    async def handler(event) -> None:
        chat = await event.get_chat()
        chat_username = getattr(chat, "username", None)
        chat_id_str = f"@{chat_username}" if chat_username else str(event.chat_id)

        channel = find_channel("telegram", chat_id_str) or find_channel(
            "telegram", str(event.chat_id)
        )
        if channel is None:
            return  # não deveria acontecer (filtro já é feito no events.NewMessage), mas por segurança

        text = event.raw_text or ""
        message_id = str(event.id)

        image_path = None
        if event.photo:
            try:
                image_bytes = await event.download_media(bytes)
                image_path = save_image_bytes("telegram", message_id, image_bytes)
            except Exception:  # noqa: BLE001
                logger.exception("Falha ao baixar foto da mensagem %s", message_id)

        # Engajamento: soma de reações, se disponíveis nesta mensagem
        engagement = 0
        if event.reactions:
            engagement = sum(r.count for r in event.reactions.results)

        ingest_post(
            platform="telegram",
            group_id=chat_id_str,
            group_label=channel.get("label", chat_id_str),
            message_id=message_id,
            text=text,
            image_path=image_path,
            posted_at=event.date,
            category_default=channel.get("category"),
            engagement_score=engagement,
        )

    logger.info(
        "Conectado. Escutando %d/%d canais/grupos configurados (resolvidos com sucesso).",
        len(resolved_chats),
        len(chat_ids),
    )
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
