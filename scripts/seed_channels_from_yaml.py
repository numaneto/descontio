"""Seed único: importa config/channels.yaml pra tabela `channels` no banco
(idempotente — se o canal já existe pelo PK platform+chat_id, só atualiza
label/category, preservando enabled/hide_brand se já tiverem sido
alterados pela admin UI). Rodar uma vez na migração pra Channel; depois
disso config/channels.yaml pode ficar desatualizado sem problema, a
aplicação não lê mais dele.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from sqlmodel import select

from app.config import CHANNELS_CONFIG_PATH
from app.db import get_session, init_db
from app.models import Channel


def seed() -> None:
    init_db()
    if not CHANNELS_CONFIG_PATH.exists():
        print(f"{CHANNELS_CONFIG_PATH} não existe, nada pra importar.")
        return

    with open(CHANNELS_CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    entries = data.get("channels", [])

    created, updated = 0, 0
    with get_session() as session:
        for entry in entries:
            platform = entry["platform"]
            chat_id = str(entry["chat_id"])
            existing = session.exec(
                select(Channel).where(Channel.platform == platform, Channel.chat_id == chat_id)
            ).first()
            if existing:
                existing.label = entry.get("label", existing.label)
                existing.category = entry.get("category")
                session.add(existing)
                updated += 1
            else:
                session.add(
                    Channel(
                        platform=platform,
                        chat_id=chat_id,
                        label=entry.get("label", chat_id),
                        category=entry.get("category"),
                    )
                )
                created += 1
        session.commit()
    print(f"Seed concluído: {created} canais criados, {updated} atualizados.")


if __name__ == "__main__":
    seed()
