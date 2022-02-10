from __future__ import annotations

__all__ = ["dict_from_exposure", "find_exposures"]

import asyncio
import datetime
import functools
import http
import re
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
    registry: int = fastapi.Query(
        default=1,
        description="Which registry to search: 1 or 2 (if it exists).",
        ge=1,
        le=2,
    ),
    instrument: str = fastapi.Query(
        default=...,
        description="Name of instrument (e.g. LSSTCam)",
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
    group_names: typing.Optional[typing.List[str]] = fastapi.Query(
        default=None,
        description="String group identifiers associated with exposures "
        "by the acquisition system. Repeat the parameter for each value.",
    ),
    observation_reasons: typing.Optional[typing.List[str]] = fastapi.Query(
        default=None,
        description="Observation types (e.g. dark, bias, science). "
        "Repeat the parameter for each value.",
    ),
    observation_types: typing.Optional[typing.List[str]] = fastapi.Query(
        default=None,
        description="Reasons the exposure was taken "
        "(e.g. science, filter scan, unknown). "
        "Repeat the parameter for each value.",
    ),
    min_date: typing.Optional[datetime.datetime] = fastapi.Query(
        default=None,
        description="Minimum date during the time the exposure was taken, exclusive "
        "(because that is how daf_butler performs a timespan overlap search). "
        "TAI as an ISO string with no timezone information. "
        "The date and time portions may be separated with a space or a T.",
    ),
    max_date: typing.Optional[datetime.datetime] = fastapi.Query(
        default=None,
        description="Maximum date during the time the exposure was taken, inclusive "
        "(because that is how daf_butler performs a timespan overlap search). "
        "TAI as an ISO string (with or without a T) with no timezone information. "
        "The date and time portions may be separated with a space or a T.",
    ),
    order_by: typing.Optional[typing.List[str]] = fastapi.Query(
        default=None,
        description="Fields to sort by. "
        "Prefix a name with - for descending order, e.g. -obs_id. "
        "Repeat the parameter for each value. "
        "The default order is 'id' (oldest first), and this is always "
        "appended if you do not explicitly specify 'id' or '-id'.\n"
        "To order by date, specify 'id' (oldest first, the default order) "
        "or '-id' (newest first). You may also search by 'timespan.begin' "
        "or 'timespan.end' if you prefer. "
        "Warning: the only safe order for use with 'offset' with 'limit' "
        "is 'id' (oldest first) if images are being added to the registry "
        "while you search.",
    ),
    offset: typing.Optional[int] = fastapi.Query(
        default=None,
        description="The number of records to skip.",
        ge=0,
    ),
    limit: int = fastapi.Query(
        default=DEFAULT_LIMIIT,
        description="The maximum number of records to return.",
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
    if registry == 2 and len(state.registries) < 2:
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail=f"registry={registry} but no second registry configured",
        )
    registry_instance = state.registries[registry - 1]

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

    # Work around two daf_butler registry.queryDimensionRecords bugs:
    # * Specifying the instrument argument results in a LookupError
    #   if the instrument is unknown. Specifying the instrument in ``where``
    #   correctly returns no records, instead.
    # * ``instrument`` cannot be specified in the ``bind`` argument.
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9-_]+$", instrument):
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail=f"Invalid instrument name {instrument!r}",
        )
    conditions = [f"instrument = '{instrument}'"]
    bind = dict()
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

    where = " and ".join(conditions)

    if order_by is None:
        order_by = ["id"]
    else:
        for fieldname in order_by:
            if fieldname in ("id", "-id"):
                break
        else:
            order_by.append("id")

    loop = asyncio.get_running_loop()
    find_func = functools.partial(
        find_exposures_in_a_registry,
        registry=registry_instance,
        bind=bind,
        where=where,
        order_by=order_by,
        offset=offset,
        limit=limit,
    )
    rows = await loop.run_in_executor(None, find_func)

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


def find_exposures_in_a_registry(
    registry: lsst.daf.butler.Registry,
    bind: dict,
    where: str,
    order_by: typing.List[str],
    offset: typing.Optional[int] = None,
    limit: int = 50,
) -> typing.List[lsst.daf.butler.core.DimensionRecord]:
    """Find exposures matching specified criteria.

    The exposures are sorted by obs_id.

    Parameters
    ----------
    registry
        The data registry to search.
    bind
        bind argument to `lsst.daf.butler.Registry.queryDimensionRecords`.
    where
        where argument to `lsst.daf.butler.Registry.queryDimensionRecords`.
    limit
        Maximum number of exposures to return.
    offset
        Starting point. None acts as 0, but may take a different code
        path in the daf_butler code.
    order_by
        Ordering criteria.

    Returns
    -------
    exposures
        The matching exposures.
    """
    try:
        record_iter = registry.queryDimensionRecords(
            "exposure",
            bind=bind,
            where=where,
        )
        record_iter.limit(limit=limit, offset=offset)
        record_iter.order_by(*order_by)
        return list(record_iter)
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail=f"Error in butler query: {e!r}",
        )
