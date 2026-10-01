"""Configurações centrais do descont.io, lidas de variáveis de ambiente (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Telegram
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING", "")

# Banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/descontio.db")

# Mídia
MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "./media")).resolve()
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_MAX_WIDTH = int(os.getenv("IMAGE_MAX_WIDTH", "800"))
IMAGE_QUALITY = int(os.getenv("IMAGE_QUALITY", "80"))

# Retenção: após RETENTION_DAYS, a oferta é arquivada (some da busca padrão
# do portal) e a imagem física é apagada do disco (o texto/metadados ficam).
# 7 dias: ofertas e cupons mudam rápido, então o portal mantém uma janela
# curta e previsível. Ver docs/07-descontio.md (home-nw-docs).
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "7"))

# LLM fallback
LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8090/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Canais monitorados
CHANNELS_CONFIG_PATH = BASE_DIR / "config" / "channels.yaml"

# Admin (habilitar/desabilitar canais, ocultar marca) — HTTP Basic Auth
# simples, protegendo só as rotas /admin/*. Sem valor default de senha de
# propósito: se não configurado, o admin fica inacessível (falha segura)
# em vez de usar uma senha fraca conhecida.
ADMIN_USER = os.getenv("ADMIN_USER", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# Portal
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
