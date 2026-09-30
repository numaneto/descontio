"""Canais/grupos monitorados — fonte de verdade é a tabela `channels` no
banco (permite habilitar/desabilitar e ocultar marca em runtime via admin
UI, sem editar arquivo nem redeploy). `config/channels.yaml` continua
existindo só como seed inicial (ver scripts/seed_channels_from_yaml.py).
"""
from sqlmodel import select

from app.db import get_session
from app.models import Channel


def load_channels(*, only_enabled: bool = True) -> list[dict]:
    """Lista de canais no mesmo formato usado antes (dict com platform/
    chat_id/label/category), pra não quebrar os callers existentes
    (poll_telegram.py, routes_api.py). `only_enabled=True` (padrão) é o
    que a ingestão deve usar; a admin UI passa False pra listar todos."""
    with get_session() as session:
        channels = session.exec(select(Channel)).all()
    return [
        {
            "platform": c.platform,
            "chat_id": c.chat_id,
            "label": c.label,
            "category": c.category,
            "enabled": c.enabled,
            "hide_brand": c.hide_brand,
        }
        for c in channels
        if (c.enabled or not only_enabled)
    ]


def find_channel(platform: str, chat_id: str) -> dict | None:
    for channel in load_channels(only_enabled=False):
        if channel["platform"] == platform and str(channel["chat_id"]) == str(chat_id):
            return channel
    return None


def is_brand_hidden(platform: str, chat_id: str) -> bool:
    channel = find_channel(platform, chat_id)
    return bool(channel and channel.get("hide_brand"))
