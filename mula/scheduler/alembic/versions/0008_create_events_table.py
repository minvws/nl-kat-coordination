"""Create events table

Revision ID: 0008
Revises: 0007
Create Date: 2023-11-14 15:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

import scheduler

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    # Add events table
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("task_id", scheduler.utils.datastore.GUID(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("context", sa.String(), nullable=True),
        sa.Column("event", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_events_task_id"), "events", ["task_id"], unique=False)


def downgrade():
    # Drop the events table
    op.drop_table("events")
