"""adiciona subcategorias (parent_id) a taxonomia existente

Revision ID: 0007_subcategories
Revises: 0006_money_categories
Create Date: 2026-10-01

Migração só de dados: cria subcategorias como filhas das categorias de
nível 1 já existentes (via `parent_id`), sem alterar schema. A lista aqui é
intencionalmente fixa/duplicada em relação a `app/categories.py` — migrações
não devem depender de constantes que podem mudar no código da aplicação no
futuro (ver padrão já usado em 0006_money_categories).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_subcategories"
down_revision: Union[str, None] = "0006_money_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (categoria-pai, [(nome, slug), ...])
SUBCATEGORIES = (
    ("informatica", (
        ("Placas de vídeo", "placas-de-video"),
        ("Notebooks", "notebooks"),
        ("Componentes", "componentes"),
        ("Armazenamento e redes", "armazenamento-redes"),
        ("Periféricos", "perifericos"),
    )),
    ("celulares", (
        ("Smartphones", "smartphones"),
        ("Tablets", "tablets"),
        ("Acessórios para celular", "acessorios-celular"),
    )),
    ("games", (
        ("Consoles", "consoles"),
        ("Controles e acessórios", "controles-acessorios"),
        ("Jogos", "jogos"),
    )),
    ("eletronicos", (
        ("TV e imagem", "tv-imagem"),
        ("Áudio", "audio"),
        ("Wearables", "wearables"),
        ("Câmeras e drones", "cameras-drones"),
        ("Energia e cabos", "energia-cabos"),
    )),
    ("eletrodomesticos", (
        ("Cozinha", "cozinha-eletro"),
        ("Lavanderia e limpeza", "lavanderia-limpeza"),
        ("Climatização", "climatizacao"),
    )),
    ("moda-beleza", (
        ("Calçados", "calcados"),
        ("Vestuário", "vestuario"),
        ("Beleza e cuidados", "beleza-cuidados"),
    )),
    ("mercado", (
        ("Bebidas", "bebidas"),
        ("Alimentos", "alimentos"),
        ("Limpeza e higiene", "limpeza-higiene"),
    )),
    ("esporte-lazer", (
        ("Fitness", "fitness"),
        ("Camping e aventura", "camping-aventura"),
        ("Esportes com bola e rodas", "esportes-bola-rodas"),
    )),
    ("ferramentas-automotivo", (
        ("Ferramentas", "ferramentas"),
        ("Automotivo", "automotivo"),
        ("Proteção", "protecao-automotiva"),
    )),
    ("viagens-servicos", (
        ("Passagens e hospedagem", "passagens-hospedagem"),
        ("Assinaturas e seguros", "assinaturas-seguros"),
    )),
    ("casa-cozinha", (
        ("Cozinha", "cozinha-utensilios"),
        ("Cama, mesa e banho", "cama-mesa-banho"),
        ("Móveis", "moveis"),
        ("Iluminação e hidráulica", "iluminacao-hidraulica"),
    )),
)


def upgrade() -> None:
    connection = op.get_bind()
    categories = sa.table(
        "categories",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("parent_id", sa.Integer()),
    )

    parent_ids = {
        row.slug: row.id
        for row in connection.execute(sa.select(categories.c.id, categories.c.slug))
    }

    rows = []
    for parent_slug, children in SUBCATEGORIES:
        parent_id = parent_ids.get(parent_slug)
        if parent_id is None:
            continue
        for name, slug in children:
            rows.append({"name": name, "slug": slug, "parent_id": parent_id})

    if rows:
        op.bulk_insert(categories, rows)


def downgrade() -> None:
    all_slugs = [slug for _parent, children in SUBCATEGORIES for _name, slug in children]
    op.execute(
        "DELETE FROM categories WHERE slug IN (%s)"
        % ",".join(f"'{slug}'" for slug in all_slugs)
    )
