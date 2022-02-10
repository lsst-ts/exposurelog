__all__ = ["SITE_ID_LEN", "create_message_table"]

import uuid

import sqlalchemy as sa
import sqlalchemy.types as saty
from sqlalchemy.dialects.postgresql import UUID

# Length of the site_id field.
SITE_ID_LEN = 16


def create_message_table() -> sa.Table:
    """Make a model of the exposurelog message table."""
    table = sa.Table(
        "message",
        sa.MetaData(),
        # See https://stackoverflow.com/a/49398042 for UUID:
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
        ),
        sa.Column("site_id", saty.Unicode(length=SITE_ID_LEN)),
        sa.Column("obs_id", saty.Unicode(), nullable=False),
        sa.Column("instrument", saty.Unicode(), nullable=False),
        sa.Column("day_obs", saty.Integer(), nullable=False),
        sa.Column("message_text", saty.UnicodeText(), nullable=False),
        sa.Column("tags", saty.ARRAY(sa.Text), nullable=False),
        sa.Column("user_id", saty.Unicode(), nullable=False),
        sa.Column("user_agent", saty.Unicode(), nullable=False),
        sa.Column("is_human", saty.Boolean(), nullable=False),
        sa.Column(
            "is_valid",
            saty.Boolean(),
            sa.Computed("date_invalidated is null"),
            nullable=False,
        ),
        sa.Column(
            "exposure_flag",
            saty.Enum(
                "none", "junk", "questionable", name="exposure_flag_enum"
            ),
            nullable=False,
        ),
        sa.Column("date_added", saty.DateTime(), nullable=False),
        sa.Column("date_invalidated", saty.DateTime(), nullable=True),
        sa.Column("parent_id", UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["message.id"]),
    )

    for name in (
        "obs_id",
        "instrument",
        "day_obs",
        "tags",
        "user_id",
        "is_valid",
        "exposure_flag",
        "date_added",
    ):
        sa.Index(f"idx_{name}", table.columns[name])

    return table
