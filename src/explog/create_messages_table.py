__all__ = ["create_messages_table"]

import typing

import sqlalchemy as sa


def create_messages_table(
    engine: typing.Optional[sa.engine.Engine] = None,
) -> sa.Table:
    """Make the exposure_log_messages sqlalchemy table.

    Return an sqlalchemy object relational model of the table
    and optionally create the table in the database.

    Parameters
    ----------
    engine
        If specified and the table does not exist in the database,
        add the table to the database.
    """
    table = sa.Table(
        "exposure_log_messages",
        sa.MetaData(),
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("obs_id", sa.String(), nullable=False),
        sa.Column("instrument", sa.String(), nullable=False),
        sa.Column("day_obs", sa.Integer(), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=False),
        sa.Column("is_human", sa.Boolean(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column(
            "exposure_flag",
            sa.Enum("none", "junk", "questionable", name="exposure_flag_enum"),
            nullable=False,
        ),
        sa.Column("date_added", sa.DateTime(), nullable=False),
        sa.Column("date_is_valid_changed", sa.DateTime(), nullable=True),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
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

    if engine is not None:
        table.metadata.create_all(engine)

    return table
