__all__ = ["SITE_ID_LEN", "create_messages_table"]

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# Length of the site_id field.
SITE_ID_LEN = 16


def create_messages_table() -> sa.Table:
    """Make the exposurelog messages table.

    Create an sqlalchemy object relational model of the table.
    """
    table = sa.Table(
        "messages",
        sa.MetaData(),
        # See https://stackoverflow.com/a/49398042 for UUID:
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
        ),
        sa.Column("site_id", sa.String(length=SITE_ID_LEN)),
        sa.Column("obs_id", sa.String(), nullable=False),
        sa.Column("instrument", sa.String(), nullable=False),
        sa.Column("day_obs", sa.Integer(), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=False),
        sa.Column("is_human", sa.Boolean(), nullable=False),
        sa.Column(
            "is_valid",
            sa.Boolean(),
            sa.Computed("date_invalidated is null"),
            nullable=False,
        ),
        sa.Column(
            "exposure_flag",
            sa.Enum("none", "junk", "questionable", name="exposure_flag_enum"),
            nullable=False,
        ),
        sa.Column("date_added", sa.DateTime(), nullable=False),
        sa.Column("date_invalidated", sa.DateTime(), nullable=True),
        sa.Column("parent_id", UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["messages.id"]),
    )

    for name in (
        "obs_id",
        "instrument",
        "day_obs",
        "user_id",
        "is_valid",
        "exposure_flag",
        "date_added",
    ):
        sa.Index(f"idx_{name}", getattr(table.c, name))

    return table
