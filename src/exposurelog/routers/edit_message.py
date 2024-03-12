__all__ = ["edit_message"]

import http

import astropy.time
import fastapi
import sqlalchemy as sa

from ..message import ExposureFlag, Message
from ..shared_state import SharedState, get_shared_state
from .normalize_tags import TAG_DESCRIPTION, normalize_tags

router = fastapi.APIRouter()


@router.patch("/messages/{id}", response_model=Message)
async def edit_message(
    id: str,
    message_text: None
    | str = fastapi.Body(default=None, description="Message text"),
    level: None
    | int = fastapi.Body(
        default=None,
        description="Message level; a python logging level.",
    ),
    tags: None
    | list[str] = fastapi.Body(
        default=None,
        description="Tags describing the message, as space-separated words. "
        "If specified, replaces the existing set of tags. " + TAG_DESCRIPTION,
    ),
    urls: None
    | list[str] = fastapi.Body(
        default=None,
        description="URLs of associated JIRA tickets, screen shots, etc.: "
        "space-separated. If specified, replaces the existing set.",
    ),
    site_id: None | str = fastapi.Body(default=None, description="Site ID"),
    user_id: None | str = fastapi.Body(default=None, description="User ID"),
    user_agent: None
    | str = fastapi.Body(
        default=None,
        description="User agent (which app created the message)",
    ),
    is_human: None
    | bool = fastapi.Body(
        default=None,
        description="Was the message created by a human being?",
    ),
    exposure_flag: None
    | ExposureFlag = fastapi.Body(
        default=None,
        description="Optional flag for troublesome exposures"
        "This flag gives users an opportunity to manually mark "
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
    message_table = state.exposurelog_db.message_table

    parent_id = id
    old_site_id = site_id

    if tags is not None:
        tags = normalize_tags(tags)

    request_data = dict(id=id, site_id=site_id)
    for name in (
        "message_text",
        "level",
        "tags",
        "urls",
        "site_id",
        "user_id",
        "user_agent",
        "is_human",
        "exposure_flag",
    ):
        value = locals()[name]
        if value is not None:
            request_data[name] = value

    async with state.exposurelog_db.engine.begin() as connection:
        # Find the parent message.
        get_parent_result = await connection.execute(
            message_table.select()
            .where(message_table.c.id == parent_id)
            .with_for_update()
        )
        parent_row = get_parent_result.fetchone()
        if parent_row is None:
            raise fastapi.HTTPException(
                status_code=http.HTTPStatus.NOT_FOUND,
                detail=f"Message with id={parent_id} not found",
            )

        # Add and get the new message.
        new_data = dict(parent_row._mapping).copy()
        new_data.update(request_data)
        for field in ("id", "is_valid", "date_invalidated"):
            del new_data[field]
        current_tai = astropy.time.Time.now().tai.datetime
        new_data["site_id"] = state.site_id
        new_data["date_added"] = current_tai
        new_data["parent_id"] = parent_id
        add_row = await connection.execute(
            message_table.insert()
            .values(**new_data)
            .returning(sa.literal_column("*"))
        )
        add_row = add_row.fetchone()

        # Mark the parent message as invalid.
        await connection.execute(
            message_table.update()
            .where(message_table.c.id == parent_id)
            .values(date_invalidated=current_tai)
        )

    return Message.model_validate(add_row)
