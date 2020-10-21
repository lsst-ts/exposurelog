from __future__ import annotations

__all__ = ["delete_messages"]

import typing

import astropy.time
import sqlalchemy

from owl.dict_from_result_proxy import dict_from_result_proxy

if typing.TYPE_CHECKING:
    import aiohttp
    import graphql


async def delete_messages(
    app: aiohttp.web.Application,
    _info: graphql.GraphQLResolveInfo,
    **kwargs,
) -> dict:
    """Delete a message.

    Parameters
    ----------
    app
        aiohttp application.
    _info
        Information about this request (ignored).
    kwargs
        Message field=value data.
        The only entry used is ``id``.
    """
    owl_database = app["owl/owl_database"]

    # Validate the user data and handle defaults
    message_ids = kwargs["ids"]
    current_tai = astropy.time.Time.now().tai.iso

    # Delete the messages
    async with owl_database.engine.acquire() as connection:
        result_proxy = await connection.execute(
            owl_database.table.update()
            .where(owl_database.table.c.id.in_(message_ids))
            .values(is_valid=False, date_is_valid_changed=current_tai)
            .returning(sqlalchemy.literal_column("*"))
        )
        messages = []
        async for row in result_proxy:
            messages.append(dict_from_result_proxy(row))

    return messages
