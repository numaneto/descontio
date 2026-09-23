"""Carrega a lista de canais/grupos monitorados de config/channels.yaml."""
from functools import lru_cache

import yaml

from app.config import CHANNELS_CONFIG_PATH


@lru_cache
def load_channels() -> list[dict]:
    if not CHANNELS_CONFIG_PATH.exists():
        return []
    with open(CHANNELS_CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("channels", [])


def find_channel(platform: str, chat_id: str) -> dict | None:
    for channel in load_channels():
        if channel.get("platform") == platform and str(channel.get("chat_id")) == str(chat_id):
            return channel
    return None
