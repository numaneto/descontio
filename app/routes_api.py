"""Endpoints de ingestão via API (webhook do WhatsApp/Evolution API).

O worker do Telegram roda como processo separado e chama `ingest_post`
diretamente (mesmo processo Python, sem precisar de rota HTTP) — ver
workers/telegram_worker.py. Já o WhatsApp entra por webhook HTTP porque o
Evolution API é um serviço externo separado.
"""
import base64
import logging

from fastapi import APIRouter, Header, HTTPException, Request

from app.channels import find_channel
from app.config import WHATSAPP_WEBHOOK_SECRET
from app.ingest import ingest_post, save_image_bytes

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, x_webhook_secret: str | None = Header(default=None)):
    if not WHATSAPP_WEBHOOK_SECRET or x_webhook_secret != WHATSAPP_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="webhook secret invalido")

    payload = await request.json()

    # Formato do Evolution API (evento messages.upsert): payload["data"] tem
    # a mensagem; ajustar conforme a versão instalada, se necessário.
    data = payload.get("data", {})
    key = data.get("key", {})
    remote_jid: str = key.get("remoteJid", "")

    # Só processa canais (@newsletter) ou grupos (@g.us) explicitamente
    # cadastrados em config/channels.yaml — ignora DMs e o resto.
    channel = find_channel("whatsapp", remote_jid)
    if channel is None:
        return {"status": "ignored", "reason": "canal nao cadastrado"}

    message = data.get("message", {})
    text = (
        message.get("conversation")
        or message.get("extendedTextMessage", {}).get("text")
        or message.get("imageMessage", {}).get("caption")
        or ""
    )
    message_id = key.get("id", "")
    if not message_id:
        return {"status": "ignored", "reason": "sem message id"}

    image_path = None
    image_b64 = data.get("message", {}).get("base64")  # depende de MEDIA_BASE64 habilitado
    if image_b64:
        try:
            image_bytes = base64.b64decode(image_b64)
            image_path = save_image_bytes("whatsapp", message_id, image_bytes)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao salvar imagem do WhatsApp para %s", message_id)

    offer = ingest_post(
        platform="whatsapp",
        group_id=remote_jid,
        group_label=channel.get("label", remote_jid),
        message_id=message_id,
        text=text,
        image_path=image_path,
        category_default=channel.get("category"),
    )
    return {"status": "ingested" if offer else "duplicate"}
