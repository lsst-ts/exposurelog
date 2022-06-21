"""Add `level` and `urls` columns to the message table

Revision ID: 5fcfc236c8df
Revises: 3bb3cd14b2dd
Create Date: 2022-03-18 16:56:58.689843
"""
import logging

import sqlalchemy as sa
import sqlalchemy.types as saty

from alembic import op

# revision identifiers, used by Alembic.
revision = "5fcfc236c8df"
down_revision = "3bb3cd14b2dd"
branch_labels = None
depends_on = None

MESSAGE_TABLE_NAME = "message"


def upgrade(log: logging.Logger, table_names: set[str]) -> None:
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return
    log.info("Add 'level' and 'urls' columns")
    op.add_column(
        MESSAGE_TABLE_NAME, sa.Column("level", saty.Integer(), nullable=True)
    )
    op.add_column(
        MESSAGE_TABLE_NAME,
        sa.Column("urls", saty.ARRAY(sa.Text), nullable=True),
    )
    op.execute(f"UPDATE {MESSAGE_TABLE_NAME} SET level = 20")  # 20=info
    # "{ }" is Postgres syntax for an empty list
    op.execute(f"UPDATE {MESSAGE_TABLE_NAME} SET urls = '{{ }}'")
    op.alter_column(MESSAGE_TABLE_NAME, "level", nullable=False)
    op.alter_column(MESSAGE_TABLE_NAME, "urls", nullable=False)


def downgrade(log: logging.Logger, table_names: set[str]) -> None:
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return

    log.info("Drop 'level' and 'urls' columns")
    op.drop_column(MESSAGE_TABLE_NAME, "level")
    op.drop_column(MESSAGE_TABLE_NAME, "urls")
