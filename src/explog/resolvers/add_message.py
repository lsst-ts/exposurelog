from __future__ import annotations

__all__ = ["add_message"]

import asyncio
import typing

import astropy.time
import astropy.units as u
import lsst.daf.butler
import sqlalchemy

from explog.dict_from_result_proxy import dict_from_result_proxy

if typing.TYPE_CHECKING:
    import aiohttp
    import graphql


async def add_message(
    app: aiohttp.web.Application,
    _info: graphql.GraphQLResolveInfo,
    is_new: bool = False,
    **kwargs,
) -> dict:
    """Add a message.

    Parameters
    ----------
    app
        aiohttp application.
    _info
        Information about this request (ignored).
    is_new
        Controls what happens if the exposure is not found in either
        butler registry:

        * True: the message is added, with ``day_obs`` computed from
          the current date.
        * False: the request is rejected.
    kwargs
        Message field=value data.

    Returns
    -------
    message_data
        Full data for the new message, as field=value.
    """
    exposure_log_database = app["explog/exposure_log_database"]
    registries = app["explog/registries"]

    data_dict = kwargs.copy()
    data_dict["is_valid"] = True
    curr_tai = astropy.time.Time.now()
    data_dict["date_added"] = curr_tai.tai.iso

    # Check obs_id and determine day_obs.
    loop = asyncio.get_running_loop()
    obs_id = data_dict["obs_id"]
    day_obs = await loop.run_in_executor(
        None,
        get_day_obs_from_registries,
        registries,
        obs_id,
        data_dict["instrument"],
    )
    if day_obs is None:
        if is_new:
            exposure_start_time = curr_tai
            day_obs_full = exposure_start_time - 12 * u.hr
            day_obs = int(day_obs_full.strftime("%Y%m%d"))
        else:
            raise RuntimeError(
                f"Exposure {obs_id} not found and is_new is false"
            )

    data_dict["day_obs"] = day_obs

    # Add the message.
    async with exposure_log_database.engine.acquire() as connection:
        result_proxy = await connection.execute(
            exposure_log_database.table.insert()
            .values(**data_dict)
            .returning(sqlalchemy.literal_column("*"))
        )
        result = await result_proxy.fetchone()

    return dict_from_result_proxy(result)


ButlerList = typing.Sequence[lsst.daf.butler.Butler]


def get_day_obs_from_registries(
    registries: ButlerList, obs_id: str, instrument: str
) -> int or None:
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
