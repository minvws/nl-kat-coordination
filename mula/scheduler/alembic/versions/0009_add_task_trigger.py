"""Add tasks trigger

Revision ID: 0009
Revises: 0008
Create Date: 2023-11-14 15:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    # Create the record_event function
    op.execute(
        sa.DDL(
            """
        CREATE OR REPLACE FUNCTION record_event()
            RETURNS TRIGGER AS
        $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO events (task_id, type, context, event, data)
                VALUES (NEW.id, 'events.db', 'task', 'insert', row_to_json(NEW));
            ELSIF TG_OP = 'UPDATE' THEN
                INSERT INTO events (task_id, type, context, event, data)
                VALUES (NEW.id, 'events.db', 'task', 'update', row_to_json(NEW));
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
        )
    )

    # Create the triggers
    op.execute(
        sa.DDL(
            """
        CREATE TRIGGER tasks_insert_update_trigger
        AFTER INSERT OR UPDATE ON tasks
        FOR EACH ROW
        EXECUTE FUNCTION record_event();
    """
        )
    )


def downgrade():
    # Drop the record_event function
    op.execute(sa.DDL("DROP FUNCTION IF EXISTS record_event()"))

    # Drop the trigger
    op.execute(sa.DDL("DROP TRIGGER IF EXISTS tasks_insert_update_trigger ON tasks"))
