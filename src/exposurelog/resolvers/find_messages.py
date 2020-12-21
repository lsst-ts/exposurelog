from __future__ import annotations

__all__ = ["find_messages"]

import typing

import sqlalchemy as sa

from exposurelog.dict_from_result_proxy import dict_from_result_proxy

if typing.TYPE_CHECKING:
    import aiohttp
    import graphql


async def find_messages(
    app: aiohttp.web.Application,
    _info: graphql.GraphQLResolveInfo,
    **kwargs,
) -> dict:
    """Find messages.

    Parameters
    ----------
    app
        aiohttp application.
    _info
        Information about this request (ignored).
    kwargs
        Find conditions as field=value data.
    """
    exposurelog_db = app["exposurelog/exposurelog_db"]

    async with exposurelog_db.engine.acquire() as connection:
        conditions = []
        order_by = []
        # Handle minimums and maximums
        for key, value in kwargs.items():
            if key.startswith("min_"):
                column = getattr(exposurelog_db.table.c, key[4:])
                conditions.append(column >= value)
            elif key.startswith("max_"):
                column = getattr(exposurelog_db.table.c, key[4:])
                conditions.append(column < value)
            elif key.startswith("has_"):
                column = getattr(exposurelog_db.table.c, key[4:])
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
                column = getattr(exposurelog_db.table.c, key[:-1])
                conditions.append(column.in_(value))
            elif key in ("message_text", "obs_id"):
                column = getattr(exposurelog_db.table.c, key)
                conditions.append(column.contains(value))
            elif key in ("is_human", "is_valid"):
                column = getattr(exposurelog_db.table.c, key)
                conditions.append(column == value)
            elif key == "order_by":
                for item in value:
                    if item.startswith("-"):
                        column = getattr(exposurelog_db.table.c, item[1:])
                        order_by.append(sa.sql.desc(column))
                    else:
                        column = getattr(exposurelog_db.table.c, item)
                        order_by.append(sa.sql.asc(column))
                column = exposurelog_db.table.c.exposure_flag

            else:
                raise RuntimeError(f"Bug: unrecognized key: {key}")
        full_conditions = sa.sql.and_(*conditions)
        result_proxy = await connection.execute(
            exposurelog_db.table.select()
            .where(full_conditions)
            .order_by(*order_by)
        )
        messages = []
        async for row in result_proxy:
            messages.append(dict_from_result_proxy(row))

    return messages
