"""Cria o schema do banco de dados (rodar uma vez antes do primeiro start)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import init_db  # noqa: E402

if __name__ == "__main__":
    init_db()
    print("Banco de dados inicializado.")
