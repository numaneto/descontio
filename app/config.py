"""Configurações centrais do HubOffers, lidas de variáveis de ambiente (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Telegram
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING", "")

# WhatsApp
WHATSAPP_WEBHOOK_SECRET = os.getenv("WHATSAPP_WEBHOOK_SECRET", "")

# Banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/hub_offers.db")

# Mídia
MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "./media")).resolve()
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# LLM fallback
LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8090/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Canais monitorados
CHANNELS_CONFIG_PATH = BASE_DIR / "config" / "channels.yaml"

# Portal
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
