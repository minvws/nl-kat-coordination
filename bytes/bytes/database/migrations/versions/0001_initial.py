"""Initial migration

Revision ID: 541ec7b3d24e
Revises:
Create Date: 2021-10-19 07:43:37.479544

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "541ec7b3d24e"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "boefje_meta",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("module_path", sa.String(), nullable=False),
        sa.Column("module_version", sa.String(), nullable=True),
        sa.Column("organization", sa.String(), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("dispatches", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_table(
        "normalizer_meta",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("module_path", sa.String(), nullable=False),
        sa.Column("module_version", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("boefje_meta_id", postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["boefje_meta_id"], ["boefje_meta.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_table(
        "output_ooi",
        sa.Column("ooi_id", sa.String(), nullable=False),
        sa.Column("normalizer_meta_id", postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["normalizer_meta_id"], ["normalizer_meta.id"]),
        sa.PrimaryKeyConstraint("ooi_id", "normalizer_meta_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("output_ooi")
    op.drop_table("normalizer_meta")
    op.drop_table("boefje_meta")
    # ### end Alembic commands ###
