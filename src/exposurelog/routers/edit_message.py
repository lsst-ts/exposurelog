from __future__ import annotations

__all__ = ["edit_message"]

import astropy.time
import fastapi
import sqlalchemy as sa

from ..message import ExposureFlag, Message
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()


@router.patch("/messages/{id}", response_model=Message)
async def edit_message(
    id: str,
    message_text: str = fastapi.Body(default=None, title="Message text"),
    site_id: str = fastapi.Body(default=None, title="Site ID"),
    user_id: str = fastapi.Body(default=None, title="User ID"),
    user_agent: str = fastapi.Body(
        default=None,
        title="User agent (which app created the message)",
    ),
    is_human: bool = fastapi.Body(
        default=None,
        title="Was the message created by a human being?",
    ),
    exposure_flag: ExposureFlag = fastapi.Body(
        default=None,
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

    - Read the message to edit; call this the parent message.
    - Create a new message using the parent message data,
      overridden by the new user-supplied data.
      Set parent_id of the new message to the id of the parent message,
      in order to provide a link to the parent message.
    - Set timestamp_is_valid_changed=now on the parent message.
    """
    el_table = state.exposurelog_db.table

    parent_id = id
    old_site_id = site_id

    request_data = dict(id=id, site_id=site_id)
    for name in (
        "message_text",
        "site_id",
        "user_id",
        "user_agent",
        "is_human",
        "exposure_flag",
    ):
        value = locals()[name]
        if value is not None:
            request_data[name] = value

    # Get all data for the existing message
    async with state.exposurelog_db.engine.acquire() as connection:
        get_old_result_proxy = await connection.execute(
            el_table.select().where(el_table.c.id == parent_id)
        )
        if get_old_result_proxy.rowcount == 0:
            raise fastapi.HTTPException(
                status_code=404,
                detail=f"Message with id={parent_id} not found",
            )
        result = await get_old_result_proxy.fetchone()
    new_data = dict(result)
    new_data.update(request_data)
    for field in ("id", "is_valid", "date_invalidated"):
        new_data.pop(field)
    current_tai_iso = astropy.time.Time.now().tai.iso
    new_data["site_id"] = state.site_id
    new_data["date_added"] = current_tai_iso
    new_data["parent_id"] = parent_id

    # Add the new message and update the old one.
    # TODO: make this a single transaction (aiopg does not support that).
    async with state.exposurelog_db.engine.acquire() as connection:
        add_result_proxy = await connection.execute(
            el_table.insert()
            .values(**new_data)
            .returning(sa.literal_column("*"))
        )
        add_result = await add_result_proxy.fetchone()
        await connection.execute(
            el_table.update()
            .where(el_table.c.id == parent_id)
            .values(date_invalidated=current_tai_iso)
        )

    return Message(**add_result)
