"""Engine/sessão do banco de dados (SQLModel sobre SQLite).

Schema gerenciado via Alembic (`migrations/`) desde 2026-09-30 — `init_db()`
roda `alembic upgrade head` automaticamente (idempotente) em vez de
`SQLModel.metadata.create_all`, pra evitar divergência entre o que o ORM
espera e o schema real quando novas colunas/tabelas são adicionadas (ver
migrations/versions/0002_category_product.py)."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

from app.config import DATABASE_URL

BASE_DIR = Path(__file__).resolve().parent.parent

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def _alembic_config() -> Config:
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg


def init_db() -> None:
    from app import models  # noqa: F401  (garante que os modelos sejam registrados)

    command.upgrade(_alembic_config(), "head")


def get_session() -> Session:
    return Session(engine)
