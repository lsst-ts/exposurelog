from __future__ import annotations

__all__ = ["edit_message"]

import astropy.time
import fastapi
import sqlalchemy as sa

from ..message import ExposureFlag, Message
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter(prefix="/exposurelog")


@router.post("/edit_message/", response_model=Message)
async def edit_message(
    id: int = fastapi.Form(
        ...,
        title="ID of message to edit",
    ),
    site_id: str = fastapi.Form(
        ...,
        title="Site ID of messages to edit",
    ),
    message_text: str = fastapi.Form(None, title="Message text"),
    user_id: str = fastapi.Form(None, title="User ID"),
    user_agent: str = fastapi.Form(
        None, title="User agent (which app created the message)"
    ),
    is_human: bool = fastapi.Form(
        None, title="Was the message created by a human being?"
    ),
    exposure_flag: ExposureFlag = fastapi.Form(
        None,
        title="Optional flag for troublesome exposures",
        description="This flag gives users an opportunity to manually mark "
        "an exposure as possibly bad (questionable) or likely bad (junk). "
        "We do not expect this to be used very often, if at all; we take "
        "far too much data to expect users to manually flag problems. "
        "However, this flag may be useful for marking egregious problems, "
        "such as the mount misbehaving during an exposure.",
    ),
    state: SharedState = fastapi.Depends(get_shared_state),
) -> Message:
    """Edit an existing message.

    The process is:

    - Read the message to edit
    - Create new data using the original message data,
      overridden by the user-supplied data.
    - Add a new message.
    - Set is_valid=False and timestamp_is_valid_changed=now
      on the original message.
    """
    exposurelog_db = state.exposurelog_db

    old_message_id = id
    old_site_id = site_id

    request_data = dict(id=id, site_id=site_id)
    for name in (
        "message_text",
        "user_id",
        "user_agent",
        "is_human",
        "exposure_flag",
    ):
        value = locals()[name]
        if value is not None:
            request_data[name] = value

    # Get all data for the existing message
    async with exposurelog_db.engine.acquire() as connection:
        # async for row in conn.execute(tbl.select().where(tbl.c.val=='abc')):
        get_old_result_proxy = await connection.execute(
            exposurelog_db.table.select().where(
                sa.sql.and_(
                    exposurelog_db.table.c.id == old_message_id,
                    exposurelog_db.table.c.site_id == old_site_id,
                )
            )
        )
        if get_old_result_proxy.rowcount == 0:
            raise fastapi.HTTPException(
                status_code=404,
                detail=f"Message with id={old_message_id} not found",
            )
        result = await get_old_result_proxy.fetchone()
    new_data = dict(result)
    new_data.update(request_data)
    for field in ("id", "date_is_valid_changed"):
        new_data.pop(field)
    current_tai_iso = astropy.time.Time.now().tai.iso
    new_data["is_valid"] = True
    new_data["site_id"] = state.site_id
    new_data["date_added"] = current_tai_iso
    new_data["parent_id"] = old_message_id
    new_data["parent_site_id"] = old_site_id

    # Add the new message and update the old one.
    # TODO: make this a single transaction (aiopg does not support that).
    async with exposurelog_db.engine.acquire() as connection:
        add_result_proxy = await connection.execute(
            exposurelog_db.table.insert()
            .values(**new_data)
            .returning(sa.literal_column("*"))
        )
        add_result = await add_result_proxy.fetchone()
        await connection.execute(
            exposurelog_db.table.update()
            .where(exposurelog_db.table.c.id == old_message_id)
            .values(is_valid=False, date_is_valid_changed=current_tai_iso)
        )

    return Message(**add_result)
