__all__ = ["add_message"]

import asyncio
import collections.abc
import http
import logging
import re

import fastapi
import lsst.daf.butler
import lsst.daf.butler.registry
import sqlalchemy as sa

from ..message import ExposureFlag, Message
from ..shared_state import SharedState, get_shared_state
from ..utils import current_date_and_day_obs
from .normalize_tags import TAG_DESCRIPTION, normalize_tags

router = fastapi.APIRouter()

OBSID_REGEX = re.compile(r"[A-Z][A-Z]_[A-Z]_(\d\d\d\d\d\d\d\d)_(\d\d\d\d\d\d)")


# The pair of decorators avoids a redirect from uvicorn if the trailing "/"
# is not as expected. include_in_schema=False hides one from the API docs.
# https://github.com/tiangolo/fastapi/issues/2060
@router.post("/messages", response_model=Message)
@router.post("/messages/", response_model=Message, include_in_schema=False)
async def add_message(
    obs_id: str = fastapi.Body(
        default=..., description="Observation ID (a string)"
    ),
    instrument: str = fastapi.Body(
        default=...,
        description="Short name of instrument (e.g. LSSTCam)",
    ),
    message_text: str = fastapi.Body(..., description="Message text"),
    level: int = fastapi.Body(
        default=logging.INFO,
        description="Message level; a python logging level.",
    ),
    tags: list[str] = fastapi.Body(
        default=[],
        description="Tags describing the message, as space-separated words. "
        + TAG_DESCRIPTION,
    ),
    urls: list[str] = fastapi.Body(
        default=[],
        description="URLs of associated JIRA tickets, screen shots, etc.: "
        "space-separated.",
    ),
    user_id: str = fastapi.Body(..., description="User ID"),
    user_agent: str = fastapi.Body(
        default=...,
        description="User agent (name of application creating the message)",
    ),
    is_human: bool = fastapi.Body(
        default=...,
        description="Was the message created by a human being?",
    ),
    is_new: bool = fastapi.Body(
        default=...,
        description="Is the exposure new (and perhaps not yet ingested)?"
        "If True: the exposure need not appear in either "
        "butler registry, and if it does not, this service will compute "
        "day_obs using the current date. ",
    ),
    exposure_flag: ExposureFlag = fastapi.Body(
        default=ExposureFlag.none,
        description="Optional flag for troublesome exposures"
        "This flag gives users an opportunity to manually mark "
        "an exposure as possibly bad (questionable) or likely bad (junk). "
        "We do not expect this to be used very often, if at all; "
        "we take far too much data to expect users to manually flag problems. "
        "However, this flag may be useful for marking egregious problems, "
        "such as the mount misbehaving during an exposure.",
    ),
    state: SharedState = fastapi.Depends(get_shared_state),
) -> Message:
    """Add a message to the database and return the added message."""
    current_date, current_day_obs = current_date_and_day_obs()

    tags = normalize_tags(tags)

    # Check obs_id and determine day_obs.
    loop = asyncio.get_running_loop()

    try:
        exposure = await loop.run_in_executor(
            None,
            exposure_from_registry,
            state.registries,
            obs_id,
            instrument,
        )
    except Exception as e:
        if is_new:
            day_obs = current_day_obs
            check_obs_id(obs_id=obs_id, current_day_obs=current_day_obs)
        else:
            raise fastapi.HTTPException(
                status_code=http.HTTPStatus.NOT_FOUND, detail=str(e)
            )
    else:
        day_obs = exposure.day_obs

    message_table = state.exposurelog_db.message_table

    # Add the message.
    async with state.exposurelog_db.engine.begin() as connection:
        result = await connection.execute(
            message_table.insert()
            .values(
                site_id=state.site_id,
                obs_id=obs_id,
                instrument=instrument,
                day_obs=day_obs,
                message_text=message_text,
                level=level,
                tags=tags,
                urls=urls,
                user_id=user_id,
                user_agent=user_agent,
                is_human=is_human,
                exposure_flag=exposure_flag,
                date_added=current_date.tai.datetime,
            )
            .returning(sa.literal_column("*"))
        )
        result = result.fetchone()

    return Message.from_orm(result)


def check_obs_id(obs_id: str, current_day_obs: int) -> None:
    """Check obs_id.

    Only intended to be called if is_new is true, since otherwise obs_id
    is checked and the current seq_num retrieved with the butler.

    Parameters
    ----------
    obs_id
        obs_id of the exposure being taken.
    current_day_obs
        Current day_obs. Used to check obs_id.

    Returns
    -------
    seq_num
        The exposure sequence number.

    Raises
    ------
    fastapi.HTTPException
        If obs_id has invalid format or if the obs_day field is more
        than 1 day away from the current_obs_day.
    """
    match = OBSID_REGEX.fullmatch(obs_id)
    if match is None:
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail=f"Invalid {obs_id=}",
        )
    day_obs = int(match.groups()[0])
    if not current_day_obs - 1 <= day_obs <= current_day_obs + 1:
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail=f"Invalid {obs_id=}; {day_obs=} "
            f"not within one day of current day_obs={current_day_obs}",
        )


def exposure_from_registry(
    registries: collections.abc.Sequence[lsst.daf.butler.registry.Registry],
    obs_id: str,
    instrument: str,
) -> lsst.daf.butler.dimensions.DimensionRecord:
    """Get the day of observation of an exposure, or None if not found.

    Parameters
    ----------
    registries
        One or more data registries.
        They are searched in order.
    instrument
        Instrument name.
    obs_id
        Observation ID.

    Returns
    -------
    day_obs : `int` or `None`
        The day of observation of the exposure, if found, else None.

    Raises
    ------
    RuntimError
        If more than one matching exposure is found in a registry,
        or if no matching exposures are found in any registry.

    Notes
    -----
    The first registry that has a matching exposure is used, and the
    remaining registries are not searched.
    If a registry that is checked contains more than one matching exposure,
    raise RuntimeError.
    """
    try:
        query_str = f"exposure.obs_id='{obs_id}' and instrument='{instrument}'"
        for registry in registries:
            try:
                records = list(
                    registry.queryDimensionRecords("exposure", where=query_str)
                )
                if len(records) == 1:
                    return records[0]
                elif len(records) > 1:
                    raise RuntimeError(
                        f"Found {len(records)} > 1 exposures in {registries=} "
                        f"with {instrument=} and {obs_id=}. Is the registry corrupt?"
                    )
            except lsst.daf.butler.registry.DataIdValueError:
                # No such instrument
                continue
    except Exception as e:
        raise RuntimeError(f"Error in butler query: {e!r}")
    raise RuntimeError(
        f"No exposure found in {registries=} with {instrument=} and {obs_id=}"
    )
