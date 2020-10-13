from __future__ import annotations

__all__ = ["add_message", "get_start_time_from_registries"]

import asyncio
import typing

import astropy.time
import astropy.units as u
import lsst.daf.butler
import sqlalchemy
from aiohttp import web

from owl.dict_from_result_proxy import dict_from_result_proxy
from owl.handlers import routes

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
            registry.queryDimensionRecords(
                "exposure",
                where=query_str,
            )
        )
        if records:
            return records[0].timespan.begin
    return None


@routes.get("/add")
async def add_message(request: web.Request) -> web.Response:
    """Add a new message."""

    registries = request.config_dict["owl/registries"]
    owl_database = request.config_dict["owl/owl_database"]

    data_dict = await request.json()

    # Validate the user data and handle defaults
    validator = request.config_dict["owl/validators"]["add"]
    validator.validate(data_dict)
    data_dict.setdefault("is_valid", True)
    data_dict.setdefault("exposure_flag", None)
    curr_tai = astropy.time.Time.now()
    data_dict["date_added"] = curr_tai.tai.iso

    # Pop is_new because it is not a field in the database.
    is_new = data_dict.pop("is_new", False)

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
            raise web.HTTPInternalServerError(
                reason=f"Exposure {obs_id} not found and is_new is false"
            )

    obs_day_full = exposure_start_time - 12 * u.hr
    data_dict["day_obs"] = int(obs_day_full.strftime("%Y%m%d"))

    # Add the message.
    async with owl_database.engine.acquire() as connection:
        result_proxy = await connection.execute(
            owl_database.table.insert()
            .values(**data_dict)
            .returning(sqlalchemy.literal_column("*"))
        )
        result = await result_proxy.fetchone()

    return web.json_response(dict_from_result_proxy(result))
