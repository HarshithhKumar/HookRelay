"""add durable dm worker state

Revision ID: c4d8e51f2a36
Revises: b9e142e3c7f1
Create Date: 2026-08-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d8e51f2a36"
down_revision: Union[str, Sequence[str], None] = "b9e142e3c7f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "dm_jobs",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dm_jobs_claimed_at", "dm_jobs", ["claimed_at"], unique=False)
    op.create_table(
        "dm_rate_limit_lock",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(sa.table("dm_rate_limit_lock", sa.column("id", sa.Integer())), [{"id": 1}])
    op.create_table(
        "dm_send_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dm_job_id", sa.Uuid(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dm_job_id"], ["dm_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dm_send_attempts_attempted_at",
        "dm_send_attempts",
        ["attempted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dm_send_attempts_attempted_at", table_name="dm_send_attempts")
    op.drop_table("dm_send_attempts")
    op.drop_table("dm_rate_limit_lock")
    op.drop_index("ix_dm_jobs_claimed_at", table_name="dm_jobs")
    op.drop_column("dm_jobs", "claimed_at")
