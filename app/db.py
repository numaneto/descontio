"""Engine/sessão do banco de dados (SQLModel sobre SQLite)."""
from sqlmodel import Session, SQLModel, create_engine

from app.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    from app import models  # noqa: F401  (garante que os modelos sejam registrados)

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
