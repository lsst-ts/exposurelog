__all__ = ["dict_from_exposure", "find_exposures"]

import asyncio
import datetime
import functools
import http
import typing

import astropy.time
import fastapi
import lsst.daf.butler
import lsst.daf.butler.core
import lsst.daf.butler.registry

from ..exposure import EXPOSURE_ORDER_BY_VALUES, Exposure
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()

DEFAULT_LIMIIT = 50

ExposureOrderByFieldsSet = set(EXPOSURE_ORDER_BY_VALUES)

OrderByTranslationDict = {
    "timespan_begin": "timespan.begin",
    "-timespan_begin": "-timespan.begin",
    "timespan_end": "timespan.end",
    "-timespan_end": "-timespan.end",
}


@router.get("/exposures", response_model=list[Exposure])
@router.get(
    "/exposures/",
    response_model=list[Exposure],
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
    min_day_obs: None
    | int = fastapi.Query(
        default=None,
        description="Minimum day of observation, inclusive; "
        "an integer of the form YYYYMMDD",
    ),
    max_day_obs: None
    | int = fastapi.Query(
        default=None,
        description="Maximum day of observation, exclusive; "
        "an integer of the form YYYYMMDD",
    ),
    min_seq_num: None
    | int = fastapi.Query(
        default=None,
        description="Minimum sequence number",
    ),
    max_seq_num: None
    | int = fastapi.Query(
        default=None,
        description="Maximum sequence number",
    ),
    group_names: None
    | list[str] = fastapi.Query(
        default=None,
        description="String group identifiers associated with exposures "
        "by the acquisition system. Repeat the parameter for each value.",
    ),
    observation_reasons: None
    | list[str] = fastapi.Query(
        default=None,
        description="Observation types (e.g. dark, bias, science). "
        "Repeat the parameter for each value.",
    ),
    observation_types: None
    | list[str] = fastapi.Query(
        default=None,
        description="Reasons the exposure was taken "
        "(e.g. science, filter scan, unknown). "
        "Repeat the parameter for each value.",
    ),
    min_date: None
    | datetime.datetime = fastapi.Query(
        default=None,
        description="Minimum date during the time the exposure was taken, exclusive "
        "(because that is how daf_butler Registry performs a timespan overlap search). "
        "TAI as an ISO string with no timezone information. "
        "The date and time portions may be separated with a space or a T.",
    ),
    max_date: None
    | datetime.datetime = fastapi.Query(
        default=None,
        description="Maximum date during the time the exposure was taken, inclusive "
        "(because that is how daf_butler Registry performs a timespan overlap search). "
        "TAI as an ISO string (with or without a T) with no timezone information. "
        "The date and time portions may be separated with a space or a T.",
    ),
    order_by: None
    | list[str] = fastapi.Query(
        default=None,
        description="Fields to sort by. "
        "Prefix a name with - for descending order, e.g. -obs_id. "
        "Repeat the parameter for each value. "
        "Valid values are any field in Exposure except 'instrument'. "
        "The default order is 'id' (oldest first), and this is always "
        "appended if you do not explicitly specify 'id' or '-id'.\n"
        "To order by date, specify 'id' (oldest first, the default order) "
        "or '-id' (newest first). You may also search by 'timespan_begin' "
        "or 'timespan_end' if you prefer. "
        "Warning: if images are being added to the registry while you search, "
        "then the only safe order for use with 'offset' and 'limit' is `id' "
        "(oldest first).",
    ),
    offset: None
    | int = fastapi.Query(
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
    Be careful to specify a registry that contains data for the instrument
    you specify, else you will get no exposures. Use the ``/instruments``
    endpoint to find out which registries have data for which instruments.
    """
    if registry > len(state.registries):
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

    bind: dict[str, typing.Any] = dict()
    conditions: list[str] = []
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

    # If order_by does not include "id" then append it, to make the order
    # repeatable. Otherwise different calls can return data in different
    # orders, which is a disaster when using limit and offset.
    if order_by is None:
        order_by = ["id"]
    else:
        bad_fields = set(order_by) - ExposureOrderByFieldsSet
        if bad_fields:
            raise fastapi.HTTPException(
                status_code=http.HTTPStatus.BAD_REQUEST,
                detail=f"Invalid order_by fields: {sorted(bad_fields)}; "
                + f"allowed values are {EXPOSURE_ORDER_BY_VALUES}",
            )
        order_by = [
            OrderByTranslationDict.get(name, name) for name in order_by
        ]
        if not set(order_by) & {"id", "-id"}:
            order_by.append("id")

    loop = asyncio.get_running_loop()
    find_func = functools.partial(
        find_exposures_in_a_registry,
        registry=registry_instance,
        instrument=instrument,
        bind=bind,
        where=where,
        order_by=order_by,
        offset=offset,
        limit=limit,
    )
    rows = await loop.run_in_executor(None, find_func)

    return [Exposure(**dict_from_exposure(row)) for row in rows]


def astropy_from_datetime(
    date: None | datetime.datetime,
) -> None | astropy.time.Time:
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
    data["timespan_begin"] = getattr(timespan.begin, "datetime", None)
    data["timespan_end"] = getattr(timespan.end, "datetime", None)
    return data


def find_exposures_in_a_registry(
    registry: lsst.daf.butler.registry.Registry,
    instrument: str,
    bind: dict,
    where: str,
    order_by: list[str],
    offset: None | int = None,
    limit: int = 50,
) -> list[lsst.daf.butler.core.DimensionRecord]:
    """Find exposures matching specified criteria.

    The exposures are sorted by obs_id.

    Parameters
    ----------
    registry
        The data registry to search.
    instrument
        Name of instrument.
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
            instrument=instrument,
            bind=bind,
            where=where,
        )
        record_iter = record_iter.order_by(*order_by)
        record_iter = record_iter.limit(limit=limit, offset=offset)
        return list(record_iter)
    except lsst.daf.butler.registry.DataIdValueError:
        # No such instrument
        return []
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail=f"Error in butler query {instrument=}, {bind=}, {where=}, "
            f"{limit=}, {offset=}, {order_by=}: {e!r}",
        )
