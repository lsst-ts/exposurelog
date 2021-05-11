from __future__ import annotations

__all__ = ["add_message"]

import asyncio
import typing

import astropy.time
import astropy.units as u
import fastapi
import lsst.daf.butler
import sqlalchemy as sa

from ..message import ExposureFlag, Message
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()


@router.post("/messages/", response_model=Message)
async def add_message(
    obs_id: str = fastapi.Body(default=..., title="Observation ID (a string)"),
    instrument: str = fastapi.Body(
        default=...,
        title="Short name of instrument (e.g. HSC)",
    ),
    message_text: str = fastapi.Body(..., title="Message text"),
    user_id: str = fastapi.Body(..., title="User ID"),
    user_agent: str = fastapi.Body(
        default=...,
        title="User agent (name of application creating the message)",
    ),
    is_human: bool = fastapi.Body(
        default=...,
        title="Was the message created by a human being?",
    ),
    is_new: bool = fastapi.Body(
        default=...,
        title="Is the exposure new (and perhaps not yet ingested)?",
        description="If True: the exposure need not appear in either "
        "butler registry, and if it does not, this service will compute "
        "day_obs using the current date. ",
    ),
    exposure_flag: typing.Optional[ExposureFlag] = fastapi.Body(
        default=ExposureFlag.none,
        title="Optional flag for troublesome exposures",
        description="This flag gives users an opportunity to manually mark "
        "an exposure as possibly bad (questionable) or likely bad (junk). "
        "We do not expect this to be used very often, if at all; "
        "we take far too much data to expect users to manually flag problems. "
        "However, this flag may be useful for marking egregious problems, "
        "such as the mount misbehaving during an exposure.",
    ),
    state: SharedState = fastapi.Depends(get_shared_state),
) -> Message:
    """Add a message to the database and return the added message."""
    curr_tai = astropy.time.Time.now()

    # Check obs_id and determine day_obs.
    loop = asyncio.get_running_loop()
    obs_id = obs_id
    day_obs = await loop.run_in_executor(
        None,
        get_day_obs_from_registries,
        state.registries,
        obs_id,
        instrument,
    )
    if day_obs is None:
        if is_new:
            exposure_start_time = curr_tai
            day_obs_full = exposure_start_time - 12 * u.hr
            day_obs = int(day_obs_full.strftime("%Y%m%d"))
        else:
            raise fastapi.HTTPException(
                status_code=404,
                detail=f"Exposure obs_id={obs_id} not found and is_new is false",
            )

    day_obs = day_obs

    el_table = state.exposurelog_db.table

    # Add the message.
    async with state.exposurelog_db.engine.begin() as connection:
        result = await connection.execute(
            el_table.insert()
            .values(
                date_added=curr_tai.tai.datetime,
                day_obs=day_obs,
                exposure_flag=exposure_flag,
                instrument=instrument,
                is_human=is_human,
                message_text=message_text,
                obs_id=obs_id,
                site_id=state.site_id,
                user_agent=user_agent,
                user_id=user_id,
            )
            .returning(sa.literal_column("*"))
        )
        result = result.fetchone()

    return Message(**result)


RegistryList = typing.Sequence[lsst.daf.butler.Registry]


def get_day_obs_from_registries(
    registries: RegistryList, obs_id: str, instrument: str
) -> typing.Optional[int]:
    """Get the day of observation of an exposure, or None if not found.

    Parameters
    ----------
    registries
        One or more data registries.
        They are searched in order.
    obs_id
        Observation ID.
    instrument
        Instrument name.

    Returns
    -------
    day_obs : `int` or `None`
        The day of observation of the exposure, if found, else None.

    Notes:
    -----
    If more than one matching exposure is found,
    silently uses the first one.
    """
    try:
        query_str = f"exposure.obs_id='{obs_id}' and instrument='{instrument}'"
        for registry in registries:
            records = list(
                registry.queryDimensionRecords("exposure", where=query_str)
            )
            if records:
                return records[0].day_obs
    except Exception as e:
        print(f"Error in butler query: {e}")
    return None
