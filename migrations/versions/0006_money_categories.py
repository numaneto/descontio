"""adiciona centavos inteiros e taxonomia inicial

Revision ID: 0006_money_categories
Revises: 0005_formatter_audit_usage
Create Date: 2026-10-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_money_categories"
down_revision: Union[str, None] = "0005_formatter_audit_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORIES = (
    ("Informática e hardware", "informatica"),
    ("Celulares e acessórios", "celulares"),
    ("Eletrônicos", "eletronicos"),
    ("Games", "games"),
    ("Eletrodomésticos", "eletrodomesticos"),
    ("Casa e cozinha", "casa-cozinha"),
    ("Moda e beleza", "moda-beleza"),
    ("Mercado", "mercado"),
    ("Esporte e lazer", "esporte-lazer"),
    ("Ferramentas e automotivo", "ferramentas-automotivo"),
    ("Viagens e serviços", "viagens-servicos"),
    ("Outros", "outros"),
)


def upgrade() -> None:
    with op.batch_alter_table("offers") as batch_op:
        batch_op.add_column(sa.Column("price_cents", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("price_original_cents", sa.Integer(), nullable=True))
        batch_op.create_index("ix_offers_price_cents", ["price_cents"])

    op.execute(
        "UPDATE offers SET price_cents = CAST(ROUND(price * 100) AS INTEGER) "
        "WHERE price IS NOT NULL"
    )
    op.execute(
        "UPDATE offers SET price_original_cents = "
        "CAST(ROUND(price_original * 100) AS INTEGER) "
        "WHERE price_original IS NOT NULL"
    )

    categories = sa.table(
        "categories",
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("parent_id", sa.Integer()),
    )
    op.bulk_insert(
        categories,
        [{"name": name, "slug": slug, "parent_id": None} for name, slug in CATEGORIES],
    )


def downgrade() -> None:
    op.execute("DELETE FROM categories WHERE slug IN (%s)" % ",".join(
        f"'{slug}'" for _, slug in CATEGORIES
    ))
    with op.batch_alter_table("offers") as batch_op:
        batch_op.drop_index("ix_offers_price_cents")
        batch_op.drop_column("price_original_cents")
        batch_op.drop_column("price_cents")
