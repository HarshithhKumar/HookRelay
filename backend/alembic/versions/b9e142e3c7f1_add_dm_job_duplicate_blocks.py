"""add durable dm job duplicate block records

Revision ID: b9e142e3c7f1
Revises: 76a40d5ae940
Create Date: 2026-08-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9e142e3c7f1"
down_revision: Union[str, Sequence[str], None] = "76a40d5ae940"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a durable record for each DM job duplicate blocked by the database."""
    op.create_table(
        "dm_job_duplicate_blocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("recipient_user_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dm_job_duplicate_blocks_event_id",
        "dm_job_duplicate_blocks",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_dm_job_duplicate_blocks_recipient_user_id",
        "dm_job_duplicate_blocks",
        ["recipient_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_dm_job_duplicate_blocks_rule_id",
        "dm_job_duplicate_blocks",
        ["rule_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dm_job_duplicate_blocks_rule_id",
        table_name="dm_job_duplicate_blocks",
    )
    op.drop_index(
        "ix_dm_job_duplicate_blocks_recipient_user_id",
        table_name="dm_job_duplicate_blocks",
    )
    op.drop_index(
        "ix_dm_job_duplicate_blocks_event_id",
        table_name="dm_job_duplicate_blocks",
    )
    op.drop_table("dm_job_duplicate_blocks")
