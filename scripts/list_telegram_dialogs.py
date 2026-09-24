"""Lista todos os grupos/canais que a conta do Telegram (autenticada via
TELEGRAM_SESSION_STRING) já participa, com o chat_id pronto pra copiar pro
config/channels.yaml.

Uso:
    python scripts/list_telegram_dialogs.py

Requer TELEGRAM_API_ID/API_HASH/SESSION_STRING já preenchidos no .env
(ver scripts/telegram_login.py). Só lista grupos e canais — ignora chats
1-a-1 e o "Saved Messages", que não fazem sentido pro HubOffers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon.sessions import StringSession  # noqa: E402
from telethon.sync import TelegramClient  # noqa: E402
from telethon.tl.types import Channel, Chat  # noqa: E402

from app.config import (  # noqa: E402
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_SESSION_STRING,
)

if not (TELEGRAM_API_ID and TELEGRAM_API_HASH and TELEGRAM_SESSION_STRING):
    raise SystemExit(
        "Preencha TELEGRAM_API_ID/API_HASH/SESSION_STRING no .env antes "
        "(rode scripts/telegram_login.py primeiro)."
    )

with TelegramClient(
    StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH
) as client:
    print(f"{'chat_id':<16} {'tipo':<10} nome")
    print("-" * 70)
    for dialog in client.iter_dialogs():
        entity = dialog.entity
        if isinstance(entity, Channel):
            tipo = "canal" if entity.broadcast else "supergrupo"
        elif isinstance(entity, Chat):
            tipo = "grupo"
        else:
            continue  # ignora usuários (chat 1-a-1) e afins
        username = f"@{entity.username}" if getattr(entity, "username", None) else None
        chat_id = username or str(dialog.id)
        print(f"{chat_id:<16} {tipo:<10} {dialog.name}")
