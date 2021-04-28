from __future__ import annotations

__all__ = ["delete_messages"]

import typing

import astropy.time
import fastapi
import sqlalchemy as sa

from ..message import Message
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter(prefix="/exposurelog")


@router.post("/delete_message/", response_model=typing.List[Message])
async def delete_messages(
    ids: typing.List[int] = fastapi.Form(
        ..., title="IDs of messages to delete"
    ),
    site_id: str = fastapi.Form(..., title="Site ID of messages to delete"),
    state: SharedState = fastapi.Depends(get_shared_state),
) -> typing.List[Message]:
    """Mark one or more messages as deleted.

    Do this by setting ``is_valid`` False and updating
    ``date_is_valid_changed``. Return the deleted messages.
    """
    exposurelog_db = state.exposurelog_db

    current_tai = astropy.time.Time.now().tai.iso

    # Delete the messages
    async with exposurelog_db.engine.acquire() as connection:
        result_proxy = await connection.execute(
            exposurelog_db.table.update()
            .where(
                sa.sql.and_(
                    exposurelog_db.table.c.id.in_(ids),
                    exposurelog_db.table.c.site_id == site_id,
                )
            )
            .values(is_valid=False, date_is_valid_changed=current_tai)
            .returning(sa.literal_column("*"))
        )
        messages = []
        async for row in result_proxy:
            messages.append(Message(**row))

    return messages
