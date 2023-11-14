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
        'task_events',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('event_type', sa.String(length=10), nullable=True),
        sa.Column('task_id', scheduler.utils.datastore.GUID(), nullable=True),
        sa.Column('event_time', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create the record_task_event function
    op.execute("""
        CREATE OR REPLACE FUNCTION record_task_event()
            RETURNS TRIGGER AS
        $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO task_events (event_type, task_id, data)
                VALUES ('insert', NEW.id, row_to_json(NEW));
            ELSIF TG_OP = 'UPDATE' THEN
                INSERT INTO task_events (event_type, task_id, data)
                VALUES ('update', NEW.id, row_to_json(NEW));
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
