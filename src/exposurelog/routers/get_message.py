from __future__ import annotations

__all__ = ["get_message"]

import fastapi

from ..message import Message
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()


@router.get("/messages/{id}", response_model=Message)
async def get_message(
    id: str,
    state: SharedState = fastapi.Depends(get_shared_state),
) -> Message:
    """Get one message."""
    el_table = state.exposurelog_db.table

    # Find the message
    async with state.exposurelog_db.engine.acquire() as connection:
        result_proxy = await connection.execute(
            el_table.select().where(el_table.c.id == id)
        )
        messages = []
        async for row in result_proxy:
            messages.append(Message(**row))

    if len(messages) == 0:
        raise fastapi.HTTPException(
            status_code=404,
            detail=f"No message found with id={id}",
        )
    return messages[0]
