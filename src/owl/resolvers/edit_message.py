from __future__ import annotations

__all__ = ["edit_message"]

import aiohttp
import astropy.time
import graphql
import sqlalchemy

from owl.dict_from_result_proxy import dict_from_result_proxy


async def edit_message(
    app: aiohttp.web.Application,
    _info: graphql.GraphQLResolveInfo,
    **kwargs,
) -> dict:
    """Edit an existing message.

    The process is:

    - Read the message to edit
    - Create new data using the original message data,
      overridden by the user-supplied data.
    - Add a new message.
    - Set is_valid=False and timestamp_is_valid_changed=now
      on the original message.

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

    request_data = kwargs.copy()

    old_message_id = request_data["id"]

    # Get all data for the existing message
    async with owl_database.engine.acquire() as connection:
        # async for row in conn.execute(tbl.select().where(tbl.c.val=='abc')):
        get_old_result_proxy = await connection.execute(
            owl_database.table.select().where(
                owl_database.table.c.id == old_message_id
            )
        )
        if get_old_result_proxy.rowcount == 0:
            raise RuntimeError(f"Message with id={old_message_id} not found")
        result = await get_old_result_proxy.fetchone()
    new_data = dict(result)
    new_data.update(request_data)
    for field in ("id", "date_is_valid_changed"):
        new_data.pop(field)
    current_tai_iso = astropy.time.Time.now().tai.iso
    new_data["is_valid"] = True
    new_data["date_added"] = current_tai_iso
    new_data["parent_id"] = old_message_id

    # Add the new message and update the old one.
    # TODO: make this a single transaction (aiopg does not support that).
    async with owl_database.engine.acquire() as connection:
        add_result_proxy = await connection.execute(
            owl_database.table.insert()
            .values(**new_data)
            .returning(sqlalchemy.literal_column("*"))
        )
        add_result = await add_result_proxy.fetchone()
        await connection.execute(
            owl_database.table.update()
            .where(owl_database.table.c.id == old_message_id)
            .values(is_valid=False, date_is_valid_changed=current_tai_iso)
        )

    return dict_from_result_proxy(add_result)
