"""Add tasks trigger

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
    # Add task_events table
    op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("task_id", scheduler.utils.datastore.GUID(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("context", sa.String(), nullable=True),
        sa.Column("event", sa.String(), nullable=True),
        sa.Column("datetime", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_task_events_task_id"), "task_events", ["task_id"], unique=False)

    # Create the record_task_event function
    op.execute("""
        CREATE OR REPLACE FUNCTION record_task_event()
            RETURNS TRIGGER AS
        $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO task_events (task_id, type, context, event, data)
                VALUES (NEW.id, 'events.db', 'task', 'insert', row_to_json(NEW));
            ELSIF TG_OP = 'UPDATE' THEN
                INSERT INTO task_events (task_id, type, context, event, data)
                VALUES (NEW.id, 'events.db', 'task', 'update', row_to_json(NEW));
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create the triggers
    op.execute("""
        CREATE TRIGGER tasks_insert_update_trigger
        AFTER INSERT OR UPDATE ON tasks
        FOR EACH ROW
        EXECUTE FUNCTION record_task_event();
    """)

def downgrade():
    # Drop the task_events table
    op.drop_table('task_events')

    # Drop the record_task_event function
    op.execute("DROP FUNCTION IF EXISTS record_task_event()")

    # Drop the trigger
    op.execute("DROP TRIGGER IF EXISTS tasks_insert_update_trigger ON tasks")
