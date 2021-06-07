from __future__ import annotations

__all__ = ["find_messages"]

import datetime
import typing

import fastapi
import sqlalchemy as sa

from ..message import ExposureFlag, Message
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()


@router.get("/messages/", response_model=typing.List[Message])
async def find_messages(
    site_ids: typing.List[str] = fastapi.Query(
        default=None,
        description="Site IDs.",
    ),
    obs_id: str = fastapi.Query(
        default=None,
        description="Observation ID (a string) contains...",
    ),
    instruments: typing.List[str] = fastapi.Query(
        default=None,
        description="Names of instruments (e.g. HSC). "
        "Repeat the parameter for each value.",
    ),
    min_day_obs: int = fastapi.Query(
        default=None,
        description="Minimum day of observation, inclusive; "
        "an integer of the form YYYYMMDD",
    ),
    max_day_obs: int = fastapi.Query(
        default=None,
        description="Maximum day of observation, exclusive; "
        "an integer of the form YYYYMMDD",
    ),
    message_text: str = fastapi.Query(
        default=None,
        description="Message text contains...",
    ),
    user_ids: typing.List[str] = fastapi.Query(
        default=None,
        description="User IDs. Repeat the parameter for each value.",
    ),
    user_agents: typing.List[str] = fastapi.Query(
        default=None,
        description="User agents (which app created the message). "
        "Repeat the parameter for each value.",
    ),
    is_human: bool = fastapi.Query(
        default=None,
        description="Was the message created by a human being?",
    ),
    is_valid: bool = fastapi.Query(
        default=True,
        description="Is the message valid? (False if deleted or superseded)",
    ),
    exposure_flags: typing.List[ExposureFlag] = fastapi.Query(
        default=None,
        description="List of exposure flag values. "
        "Repeat the parameter for each value.",
    ),
    min_date_added: datetime.datetime = fastapi.Query(
        default=None,
        description="Minimum date the exposure was added, inclusive; "
        "TAI as an ISO string with no timezone information",
    ),
    max_date_added: datetime.datetime = fastapi.Query(
        default=None,
        description="Maximum date the exposure was added, exclusive; "
        "TAI as an ISO string with no timezone information",
    ),
    has_date_invalidated: bool = fastapi.Query(
        default=None,
        description="Does this message have a non-null " "date_invalidated?",
    ),
    min_date_invalidated: datetime.datetime = fastapi.Query(
        default=None,
        description="Minimum date the is_valid flag was last toggled, inclusive, "
        "TAI as an ISO string with no timezone information",
    ),
    max_date_invalidated: datetime.datetime = fastapi.Query(
        default=None,
        description="Maximum date the is_valid flag was last toggled, exclusive, "
        "TAI as an ISO string with no timezone information",
    ),
    has_parent_id: bool = fastapi.Query(
        default=None,
        description="Does this message have a " "non-null parent ID?",
    ),
    order_by: typing.List[str] = fastapi.Query(
        default=None,
        description="Fields to sort by. "
        "Prefix a name with - for descending order, e.g. -id. "
        "Repeat the parameter for each value.",
    ),
    offset: int = fastapi.Query(
        default=0,
        description="The number of messages to skip.",
        ge=0,
    ),
    limit: int = fastapi.Query(
        default=50,
        description="The maximum number of number of messages to return.",
        gt=1,
    ),
    state: SharedState = fastapi.Depends(get_shared_state),
) -> list[Message]:
    """Find messages."""
    el_table = state.exposurelog_db.table

    # Names of selection arguments
    select_arg_names = (
        "site_ids",
        "obs_id",
        "instruments",
        "min_day_obs",
        "max_day_obs",
        "message_text",
        "user_ids",
        "user_agents",
        "is_human",
        "is_valid",
        "exposure_flags",
        "min_date_added",
        "max_date_added",
        "has_date_invalidated",
        "min_date_invalidated",
        "max_date_invalidated",
        "has_parent_id",
        "order_by",
    )

    async with state.exposurelog_db.engine.connect() as connection:
        conditions = []
        order_by_columns = []
        order_by_id = False
        # Handle minimums and maximums
        for key in select_arg_names:
            value = locals()[key]
            if value is None:
                continue
            if key.startswith("min_"):
                column = el_table.columns[key[4:]]
                conditions.append(column >= value)
            elif key.startswith("max_"):
                column = el_table.columns[key[4:]]
                conditions.append(column < value)
            elif key.startswith("has_"):
                column = el_table.columns[key[4:]]
                if value:
                    conditions.append(column != None)  # noqa
                else:
                    conditions.append(column == None)  # noqa
            elif key in (
                "site_ids",
                "instruments",
                "user_ids",
                "user_agents",
                "exposure_flags",
            ):
                # Value is a list; field name is key without the final "s".
                # Note: the list cannot be empty, because the array is passed
                # by listing the parameter once per value.
                column = el_table.columns[key[:-1]]
                conditions.append(column.in_(value))
            elif key in ("message_text", "obs_id"):
                column = el_table.columns[key]
                conditions.append(column.contains(value))
            elif key in ("is_human", "is_valid"):
                column = el_table.columns[key]
                conditions.append(column == value)
            elif key == "order_by":
                for item in value:
                    if item.startswith("-"):
                        column_name = item[1:]
                        column = el_table.columns[column_name]
                        order_by_columns.append(sa.sql.desc(column))
                    else:
                        column_name = item
                        column = el_table.columns[column_name]
                        order_by_columns.append(sa.sql.asc(column))
                    if column_name == "id":
                        order_by_id = True
                column = el_table.c.exposure_flag

            else:
                raise RuntimeError(f"Bug: unrecognized key: {key}")

        # If order_by does not include "id" then append it, to make the order
        # repeatable. Otherwise different calls can return data in different
        # orders, which is a disaster when using limit and offset.
        if not order_by_id:
            order_by_columns.append(sa.sql.asc(el_table.c.id))
        full_conditions = sa.sql.and_(*conditions)
        result = await connection.execute(
            el_table.select()
            .where(full_conditions)
            .order_by(*order_by_columns)
            .limit(limit)
            .offset(offset)
        )
        rows = result.fetchall()

    return [Message.from_orm(row) for row in rows]
