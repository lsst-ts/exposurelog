__all__ = ["create_messages_table"]

import sqlalchemy as sa


def create_messages_table(create_indices: bool) -> sa.Table:
    """Make the owl_messages sqlalchemy table and, optionally, the indices.

    This is a model of the owl_messages database table
    that can be used to query the database and modify rows.

    It can also be used to create a new table, and if you plan to
    use it for that then you should set ``create_indices = True``
    (the indices are only relevant when creating a new database table).
    """
    table = sa.Table(
        "owl_messages",
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

    if create_indices:
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
