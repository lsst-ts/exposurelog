"""add seq_num field

Revision ID: 396bb1f9b4ed
Revises: 5fcfc236c8df
Create Date: 2023-04-12 11:07:26.703207

"""
import logging

import sqlalchemy as sa
import sqlalchemy.types as saty

# Use type: ignore because alembic.context is only available for env.py
# when it is executed through the alembic command.
from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = "396bb1f9b4ed"
down_revision = "5fcfc236c8df"
branch_labels = None
depends_on = None


MESSAGE_TABLE_NAME = "message"


def upgrade(log: logging.Logger, table_names: set[str]) -> None:
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return
    log.info("Add 'seq_num' column")
    op.add_column(
        MESSAGE_TABLE_NAME, sa.Column("seq_num", saty.Integer(), nullable=True)
    )
    op.execute(
        f"UPDATE {MESSAGE_TABLE_NAME} "
        "SET seq_num = cast(substring(obs_id, 15) as integer)"
    )
    op.alter_column(MESSAGE_TABLE_NAME, "seq_num", nullable=False)


def downgrade(log: logging.Logger, table_names: set[str]) -> None:
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return

    log.info("Drop 'seq_num' column")
    op.drop_column(MESSAGE_TABLE_NAME, "seq_num")
