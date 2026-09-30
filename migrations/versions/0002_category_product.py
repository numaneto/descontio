"""adiciona categories, products e FKs opcionais em offers

Schema pra classificacao estruturada de ofertas (Classe/Subclasse, ex.:
"Hardware" -> "GPUs", "Camping" -> "Barracas") discutido com o usuario:
`Category` e uma arvore auto-referenciada (parent_id), `Product` e a
entidade canonica que varias `Offer` (posts brutos) podem compartilhar
depois de classificadas. Tudo nullable em `offers` de proposito - nenhuma
oferta existente ou futura fica bloqueada por falta de classificacao; o
preenchimento (manual ou via LLM) e um passo posterior, fora do escopo
desta migracao.

Revision ID: 0002_category_product
Revises: 0001_baseline
Create Date: 2026-09-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_category_product"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, index=True),
        sa.Column("slug", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True, index=True),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, index=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    with op.batch_alter_table("offers") as batch_op:
        batch_op.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("product_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_offers_category_id", ["category_id"])
        batch_op.create_index("ix_offers_product_id", ["product_id"])


def downgrade() -> None:
    with op.batch_alter_table("offers") as batch_op:
        batch_op.drop_column("product_id")
        batch_op.drop_column("category_id")
    op.drop_table("products")
    op.drop_table("categories")
