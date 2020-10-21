from __future__ import annotations

__all__ = ["find_messages"]

import typing

import sqlalchemy.sql as sql

from owl.dict_from_result_proxy import dict_from_result_proxy

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
    owl_database = app["owl/owl_database"]

    async with owl_database.engine.acquire() as connection:
        conditions = []
        order_by = []
        # Handle minimums and maximums
        for key, value in kwargs.items():
            if key.startswith("min_"):
                column = getattr(owl_database.table.c, key[4:])
                conditions.append(column >= value)
            elif key.startswith("max_"):
                column = getattr(owl_database.table.c, key[4:])
                conditions.append(column < value)
            elif key.startswith("has_"):
                column = getattr(owl_database.table.c, key[4:])
                if value:
                    conditions.append(column != None)  # noqa
                else:
                    conditions.append(column == None)  # noqa
            elif key in (
                "instruments",
                "user_ids",
                "user_agents",
                "exposure_flags",
            ):
                # Value is a list; field name is key without the final "s".
                column = getattr(owl_database.table.c, key[:-1])
                conditions.append(column.in_(value))
            elif key in ("message_text", "obs_id"):
                column = getattr(owl_database.table.c, key)
                conditions.append(column.contains(value))
            elif key in ("is_human", "is_valid"):
                column = getattr(owl_database.table.c, key)
                conditions.append(column == value)
            elif key == "order_by":
                for item in value:
                    if item.startswith("-"):
                        column = getattr(owl_database.table.c, item[1:])
                        order_by.append(sql.desc(column))
                    else:
                        column = getattr(owl_database.table.c, item)
                        order_by.append(sql.asc(column))
                column = owl_database.table.c.exposure_flag

            else:
                raise RuntimeError(f"Bug: unrecognized key: {key}")
        full_conditions = sql.and_(*conditions)
        result_proxy = await connection.execute(
            owl_database.table.select()
            .where(full_conditions)
            .order_by(*order_by)
        )
        messages = []
        async for row in result_proxy:
            messages.append(dict_from_result_proxy(row))

    return messages
