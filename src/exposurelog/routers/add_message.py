__all__ = ["add_message"]

import asyncio
import http
import logging
import re

import astropy.time
import fastapi
import lsst.daf.butler
import lsst.daf.butler.registry
import sqlalchemy as sa

from ..butler_factory import ButlerFactory
from ..message import ExposureFlag, Message
from ..shared_state import SharedState, get_shared_state
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
        description="DEPRECATED and IGNORED. "
        "The exposure must exist in a registry.",
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
    current_date = current_date = astropy.time.Time.now()

    tags = normalize_tags(tags)

    # Check obs_id and determine day_obs.
    loop = asyncio.get_running_loop()

    try:
        exposure = await loop.run_in_executor(
            None,
            exposure_from_registry,
            state.butler_factory,
            instrument,
            obs_id,
        )
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND, detail=str(e)
        )
    else:
        day_obs = exposure.day_obs
        seq_num = exposure.seq_num

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
                seq_num=seq_num,
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

    return Message.model_validate(result)


def exposure_from_registry(
    butler_factory: ButlerFactory,
    instrument: str,
    obs_id: str,
) -> lsst.daf.butler.dimensions.DimensionRecord:
    """Get the metadata associated with an exposure, or None if not found.

    Parameters
    ----------
    butler_factory: ButlerFactory
        Factory object that can be used to create one or more Butler instances.
        They are searched in order.
    instrument : `str`
        Instrument name.
    obs_id : `str`
        Observation ID.

    Returns
    -------
    exposure : `lsst.daf.butler.dimensions.DimensionRecord`
        The found exposure record.

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
        for butler in butler_factory.get_all_butlers():
            try:
                records = list(
                    butler.registry.queryDimensionRecords(
                        "exposure", where=query_str
                    )
                )
                if len(records) == 1:
                    return records[0]
                elif len(records) > 1:
                    raise RuntimeError(
                        f"Found {len(records)} > 1 exposures in {butler=} "
                        f"with {instrument=} and {obs_id=}. Is the registry corrupt?"
                    )
            except lsst.daf.butler.registry.DataIdValueError:
                # No such instrument.
                continue
    except Exception as e:
        raise RuntimeError(f"Error in butler query: {e!r}")
    raise RuntimeError(
        f"No exposure found in registries={butler_factory.config_urls}"
        f" with {instrument=} and {obs_id=}"
    )
