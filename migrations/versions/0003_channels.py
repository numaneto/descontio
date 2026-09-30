"""adiciona tabela channels (fonte de verdade em runtime pra habilitar/
desabilitar canais e ocultar marca, substituindo o config/channels.yaml
estatico)

Revision ID: 0003_channels
Revises: 0002_category_product
Create Date: 2026-09-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_channels"
down_revision: Union[str, None] = "0002_category_product"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "channels",
        sa.Column("platform", sa.String(), primary_key=True),
        sa.Column("chat_id", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true(), index=True),
        sa.Column("hide_brand", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_table("channels")
