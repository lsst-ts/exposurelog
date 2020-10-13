from __future__ import annotations

__all__ = ["delete_message"]

import astropy.time
import sqlalchemy
from aiohttp import web

from owl.dict_from_result_proxy import dict_from_result_proxy
from owl.handlers import routes


@routes.get("/delete")
async def delete_message(request: web.Request) -> web.Response:
    """Delete an existing message (set is_valid false)."""
    data_dict = await request.json()
    owl_database = request.config_dict["owl/owl_database"]

    # Validate the user data and handle defaults
    validator = request.config_dict["owl/validators"]["delete"]
    validator.validate(data_dict)
    message_id = data_dict["id"]
    current_tai = astropy.time.Time.now().tai.iso

    # Delete the message
    async with owl_database.engine.acquire() as connection:
        result_proxy = await connection.execute(
            owl_database.table.update()
            .where(owl_database.table.c.id == message_id)
            .values(is_valid=False, date_is_valid_changed=current_tai)
            .returning(sqlalchemy.literal_column("*"))
        )
        if result_proxy.rowcount == 0:
            raise web.HTTPInternalServerError(
                reason=f"Message with id={message_id} not found"
            )
        result = await result_proxy.fetchone()

    return web.json_response(dict_from_result_proxy(result))
