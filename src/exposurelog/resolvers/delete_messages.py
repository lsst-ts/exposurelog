from __future__ import annotations

__all__ = ["delete_messages"]

import typing

import astropy.time
import sqlalchemy as sa

from exposurelog.dict_from_result_proxy import dict_from_result_proxy

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
    exposure_log_database = app["exposurelog/exposure_log_database"]

    # Validate the user data and handle defaults
    message_ids = kwargs["ids"]
    current_tai = astropy.time.Time.now().tai.iso

    # Delete the messages
    async with exposure_log_database.engine.acquire() as connection:
        result_proxy = await connection.execute(
            exposure_log_database.table.update()
            .where(exposure_log_database.table.c.id.in_(message_ids))
            .values(is_valid=False, date_is_valid_changed=current_tai)
            .returning(sa.literal_column("*"))
        )
        messages = []
        async for row in result_proxy:
            messages.append(dict_from_result_proxy(row))

    return messages
