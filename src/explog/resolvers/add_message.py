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
    exposure_start_time = await loop.run_in_executor(
        None,
        get_start_time_from_registries,
        registries,
        data_dict["obs_id"],
        data_dict["instrument"],
    )
    if exposure_start_time is None:
        if is_new:
            exposure_start_time = curr_tai
        else:
            obs_id = data_dict["obs_id"]
            raise RuntimeError(
                f"Exposure {obs_id} not found and is_new is false"
            )

    obs_day_full = exposure_start_time - 12 * u.hr
    data_dict["day_obs"] = int(obs_day_full.strftime("%Y%m%d"))

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


def get_start_time_from_registries(
    registries: ButlerList, obs_id: str, instrument: str
) -> astropy.time.Time:
    """Get the obs_day of a specified exposure, or None if not found.

    Parameters
    ----------
    registries
        One or more data registries.
        They are searched in order.
    obs_id
        Observation ID.
    instrument
        Instrument name.

    Notes:
    -----
    If more than one matching exposure is found,
    silently uses the first one.
    """
    query_str = f"exposure.name = '{obs_id}' and instrument='{instrument}'"
    for registry in registries:
        records = list(
            registry.queryDimensionRecords("exposure", where=query_str)
        )
        if records:
            return records[0].timespan.begin
    return None
