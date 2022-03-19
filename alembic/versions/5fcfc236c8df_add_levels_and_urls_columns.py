"""Add `level` and `urls` columns to the message table

Revision ID: 5fcfc236c8df
Revises: 3bb3cd14b2dd
Create Date: 2022-03-18 16:56:58.689843
"""
import sqlalchemy as sa
import sqlalchemy.types as saty

from alembic import op

# revision identifiers, used by Alembic.
revision = "5fcfc236c8df"
down_revision = "3bb3cd14b2dd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("message", sa.Column("level", saty.Integer(), nullable=True))
    op.add_column(
        "message", sa.Column("urls", saty.ARRAY(sa.Text), nullable=True)
    )
    op.execute("UPDATE message SET level = 20")  # info
    op.execute("UPDATE message SET urls = '{ }'")
    op.alter_column("message", "level", nullable=False)
    op.alter_column("message", "urls", nullable=False)


def downgrade():
    op.drop_column("message", "level")
    op.drop_column("message", "urls")
