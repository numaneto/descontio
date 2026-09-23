"""Script interativo de uso único: autoriza a conta pessoal do Telegram e
gera a session string a ser colocada em TELEGRAM_SESSION_STRING no .env.

Uso:
    python scripts/telegram_login.py

Pede: número de telefone -> código recebido no Telegram -> (se houver
verificação em duas etapas) a senha. Ao final imprime a session string.

IMPORTANTE: a session string dá acesso de leitura/escrita total à conta —
trate com o mesmo cuidado que uma senha. Nunca a coloque em código-fonte ou
a comite no repositório.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon.sessions import StringSession  # noqa: E402
from telethon.sync import TelegramClient  # noqa: E402

from app.config import TELEGRAM_API_HASH, TELEGRAM_API_ID  # noqa: E402

if not (TELEGRAM_API_ID and TELEGRAM_API_HASH):
    raise SystemExit(
        "Preencha TELEGRAM_API_ID e TELEGRAM_API_HASH no .env antes de rodar este script "
        "(gere em https://my.telegram.org/apps)."
    )

with TelegramClient(StringSession(), int(TELEGRAM_API_ID), TELEGRAM_API_HASH) as client:
    session_string = client.session.save()
    print("\n=== Sessão gerada com sucesso ===")
    print("Copie a linha abaixo para TELEGRAM_SESSION_STRING no seu .env:\n")
    print(session_string)
    print()
