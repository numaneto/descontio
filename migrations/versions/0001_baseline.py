"""baseline: reflete o schema ja existente (offers, channel_poll_state)

Nao cria nada em producao (as tabelas ja existem, criadas por
SQLModel.metadata.create_all antes do Alembic existir no projeto) -
producao so precisa de `alembic stamp 0001_baseline`. Ambientes novos
(local/CI) rodam de verdade via `alembic upgrade head`.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_platform", sa.String(), nullable=False, index=True),
        sa.Column("source_group", sa.String(), nullable=False, index=True),
        sa.Column("source_label", sa.String(), nullable=False, server_default=""),
        sa.Column("source_message_id", sa.String(), nullable=False, index=True),
        sa.Column("raw_text", sa.String(), nullable=False, server_default=""),
        sa.Column("image_path", sa.String(), nullable=True),
        sa.Column("product_name", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("price_original", sa.Float(), nullable=True),
        sa.Column("coupon_code", sa.String(), nullable=True),
        sa.Column("links", sa.String(), nullable=False, server_default="[]"),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("parse_method", sa.String(), nullable=False, server_default="unmatched"),
        sa.Column("parse_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("engagement_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column("posted_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "channel_poll_state",
        sa.Column("platform", sa.String(), primary_key=True),
        sa.Column("chat_id", sa.String(), primary_key=True),
        sa.Column("last_message_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_polled_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("channel_poll_state")
    op.drop_table("offers")
