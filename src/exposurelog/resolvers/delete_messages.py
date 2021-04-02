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
    **kwargs: typing.Any,
) -> list[dict]:
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
    exposurelog_db = app["exposurelog/exposurelog_db"]

    # Validate the user data and handle defaults
    message_ids = kwargs["ids"]
    site_id = kwargs["site_id"]
    current_tai = astropy.time.Time.now().tai.iso

    # Delete the messages
    async with exposurelog_db.engine.acquire() as connection:
        result_proxy = await connection.execute(
            exposurelog_db.table.update()
            .where(
                sa.sql.and_(
                    exposurelog_db.table.c.id.in_(message_ids),
                    exposurelog_db.table.c.site_id == site_id,
                )
            )
            .values(is_valid=False, date_is_valid_changed=current_tai)
            .returning(sa.literal_column("*"))
        )
        messages = []
        async for row in result_proxy:
            messages.append(dict_from_result_proxy(row))

    return messages
