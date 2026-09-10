"""create system_config table

Revision ID: 0001
Revises:
Create Date: 2026-09-10
"""
from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_config",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), server_default="{}", nullable=False),
        sa.Column("description", sa.String(255), server_default="", nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_system_config_key", "system_config", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_system_config_key", table_name="system_config")
    op.drop_table("system_config")