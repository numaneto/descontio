"""adiciona auditoria do formatter e medição de consumo do LLM

Revision ID: 0005_formatter_audit_usage
Revises: 0004_api_keys
Create Date: 2026-10-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_formatter_audit_usage"
down_revision: Union[str, None] = "0004_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("offers") as batch_op:
        batch_op.add_column(
            sa.Column("source_links", sa.String(), nullable=False, server_default="[]")
        )

    op.create_table(
        "rejected_inputs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_platform", sa.String(), nullable=False),
        sa.Column("source_group", sa.String(), nullable=False),
        sa.Column("source_message_id", sa.String(), nullable=False),
        sa.Column("raw_text", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("rejected_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rejected_inputs_source_platform", "rejected_inputs", ["source_platform"])
    op.create_index("ix_rejected_inputs_source_group", "rejected_inputs", ["source_group"])
    op.create_index("ix_rejected_inputs_source_message_id", "rejected_inputs", ["source_message_id"])
    op.create_index("ix_rejected_inputs_rejected_at", "rejected_inputs", ["rejected_at"])
    op.create_index("ix_rejected_inputs_expires_at", "rejected_inputs", ["expires_at"])

    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_llm_usage_events_model", "llm_usage_events", ["model"])
    op.create_index("ix_llm_usage_events_operation", "llm_usage_events", ["operation"])
    op.create_index("ix_llm_usage_events_created_at", "llm_usage_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_events_created_at", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_operation", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_model", table_name="llm_usage_events")
    op.drop_table("llm_usage_events")
    op.drop_index("ix_rejected_inputs_expires_at", table_name="rejected_inputs")
    op.drop_index("ix_rejected_inputs_rejected_at", table_name="rejected_inputs")
    op.drop_index("ix_rejected_inputs_source_message_id", table_name="rejected_inputs")
    op.drop_index("ix_rejected_inputs_source_group", table_name="rejected_inputs")
    op.drop_index("ix_rejected_inputs_source_platform", table_name="rejected_inputs")
    op.drop_table("rejected_inputs")
    with op.batch_alter_table("offers") as batch_op:
        batch_op.drop_column("source_links")
