"""Size limit hash

Revision ID: 0005
Revises: 0004
Create Date: 2023-04-24 10:51:02.820727

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("items", "hash", existing_type=sa.String(), type_=sa.String(length=32), existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("items", "hash", existing_type=sa.String(length=32), type_=sa.String(), existing_nullable=True)
    # ### end Alembic commands ###