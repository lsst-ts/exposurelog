from __future__ import annotations

__all__ = ["dict_from_exposure", "find_exposures"]

import asyncio
import datetime
import http
import typing

import astropy.time
import fastapi
import lsst.daf.butler
import lsst.daf.butler.core

from ..exposure import Exposure
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()

DEFAULT_LIMIIT = 50


@router.get("/exposures", response_model=typing.List[Exposure])
@router.get(
    "/exposures/",
    response_model=typing.List[Exposure],
    include_in_schema=False,
)
async def find_exposures(
    instrument: str = fastapi.Query(
        default=...,
        description="Names of instrument (e.g. HSC)",
    ),
    min_day_obs: typing.Optional[int] = fastapi.Query(
        default=None,
        description="Minimum day of observation, inclusive; "
        "an integer of the form YYYYMMDD",
    ),
    max_day_obs: typing.Optional[int] = fastapi.Query(
        default=None,
        description="Maximum day of observation, exclusive; "
        "an integer of the form YYYYMMDD",
    ),
    min_seq_num: typing.Optional[int] = fastapi.Query(
        default=None,
        description="Minimum sequence number",
    ),
    max_seq_num: typing.Optional[int] = fastapi.Query(
        default=None,
        description="Maximum sequence number",
    ),
    group_names: typing.List[str] = fastapi.Query(
        default=None,
        description="String group identifiers associated with exposures "
        "by the acquisition system. Repeat the parameter for each value.",
    ),
    observation_reasons: typing.List[str] = fastapi.Query(
        default=None,
        description="Observation types (e.g. dark, bias, science). "
        "Repeat the parameter for each value.",
    ),
    observation_types: typing.List[str] = fastapi.Query(
        default=None,
        description="Reasons the exposure was taken "
        "(e.g. science, filter scan, unknown). "
        "Repeat the parameter for each value.",
    ),
    min_date: typing.Optional[datetime.datetime] = fastapi.Query(
        default=None,
        description="Minimum date during the time the exposure was taken, *exclusive*; "
        "TAI as an ISO string with no timezone information",
    ),
    max_date: typing.Optional[datetime.datetime] = fastapi.Query(
        default=None,
        description="Maximum date during the time the exposure was taken, exclusive; "
        "TAI as an ISO string with no timezone information",
    ),
    limit: int = fastapi.Query(
        default=DEFAULT_LIMIIT,
        description="Maximum number of records to return.",
        gt=0,
    ),
    state: SharedState = fastapi.Depends(get_shared_state),
) -> list[Exposure]:
    """Find exposures.

    Warnings
    --------
    This does not yet support pagination or ordering, because daf_butler
    Registry does not. It does, however, support ``limit``, in order to avoid
    performance issues for overly broad queries.
    """
    registries = state.registries

    # Names of selection arguments;
    # note that min_date and max_date are handled separately.
    select_arg_names = (
        "min_day_obs",
        "max_day_obs",
        "min_seq_num",
        "max_seq_num",
        "group_names",
        "observation_reasons",
        "observation_types",
    )

    conditions = []
    bind = dict()
    date_search = None
    for key in select_arg_names:
        value = locals()[key]
        if value is None:
            continue
        if key.startswith("min_"):
            column = key[4:]
            bind[key] = value
            conditions.append(f"exposure.{column} >= {key}")
        elif key.startswith("max_"):
            column = key[4:]
            bind[key] = value
            conditions.append(f"exposure.{column} < {key}")
        elif key in (
            "group_names",
            "observation_reasons",
            "observation_types",
        ):
            # Value is a list; field name is key without the final "s".
            # Note: the list cannot be empty, because the array is passed
            # by listing the parameter once per value.
            column = key[:-1]
            new_bind = {f"{key}_{i}": item for i, item in enumerate(value)}
            bind.update(new_bind)
            keys_str = "(" + ", ".join(new_bind.keys()) + ")"
            conditions.append(f"exposure.{column} IN {keys_str}")
        else:
            raise RuntimeError(f"Bug: unrecognized key: {key}")

    if min_date is not None or max_date is not None:
        bind["date_span"] = lsst.daf.butler.Timespan(
            begin=astropy_from_datetime(min_date),
            end=astropy_from_datetime(max_date),
        )
        conditions.append("exposure.timespan OVERLAPS date_span")

    # If order_by does not include "id" then append it, to make the order
    # repeatable. Otherwise different calls can return data in different
    # orders, which is a disaster when using limit and offset.
    where = " and ".join(conditions)

    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(
        None,
        find_exposures_in_registries,
        state.registries,
        instrument,
        bind,
        where,
        limit,
    )

    exposures = [Exposure(**dict_from_exposure(row)) for row in rows]
    return sorted(exposures, key=lambda exposure: exposure.obs_id)


def astropy_from_datetime(
    date: typing.Optional[datetime.datetime],
) -> typing.Optional[astropy.time.Time]:
    """Convert an optional TAI datetime.datetime to an astropy.time.Time.

    Return None if date is None.
    """
    if date is None:
        return None
    return astropy.time.Time(date, scale="tai")


def dict_from_exposure(
    exposure: lsst.daf.butler.core.DimensionRecord,
) -> dict:
    data = exposure.toDict()
    timespan = data.pop("timespan")
    data["timespan_begin"] = timespan.begin.datetime
    data["timespan_end"] = timespan.end.datetime
    return data


def find_exposures_in_registries(
    registries: typing.Sequence[lsst.daf.butler.Registry],
    instrument: str,
    bind: dict,
    where: str,
    limit: int = 50,
) -> typing.ValuesView[lsst.daf.butler.core.DimensionRecord]:
    """Find exposures matching specified criteria.

    The exposures are sorted by obs_id.

    Parameters
    ----------
    registries
        One or more data registries.
        They are searched in order.
    instrument
        Name of instrument.
    bind
        bind argument to `lsst.daf.butler.Registry.queryDimensionRecords`.
    where
        where argument to `lsst.daf.butler.Registry.queryDimensionRecords`.
    limit
        Maximum number of exposures to return.

    Returns
    -------
    exposures
        The matching exposures.

    Notes
    -----
    There is no pagination support because daf_butler does not support it.
    The limit argument merely prevents performance issues from overly
    broad searches.
    """
    # Keep records in a dict to avoid duplicates
    # (which will only be a problem if we have two registries).
    record_dict: typing.Dict[
        int, lsst.daf.butler.core.DimensionRecord
    ] = dict()
    for registry in registries:
        if len(record_dict) >= limit:
            break
        try:
            record_iter = registry.queryDimensionRecords(
                "exposure",
                instrument=instrument,
                bind=bind,
                where=where,
            )
            for record in record_iter:
                # Use dict.setdefault so the first instance "wins",
                # though the records should match in each registry.
                record_dict.setdefault(record.id, record)
                if len(record_dict) >= limit:
                    break
        except Exception as e:
            raise fastapi.HTTPException(
                status_code=http.HTTPStatus.NOT_FOUND,
                detail=f"Error in butler query: {e!r}",
            )
    return record_dict.values()
