from __future__ import annotations

__all__ = ["get_instruments"]

import asyncio
import typing

import fastapi
import pydantic

if typing.TYPE_CHECKING:
    import lsst.daf.butler

from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()


class Config(pydantic.BaseModel):
    butler_instruments_1: typing.List[str] = pydantic.Field(
        description="Instruments supported by butler 1."
    )
    butler_instruments_2: typing.List[str] = pydantic.Field(
        description="Instruments supported by butler 2; "
        "'[]' if there is only one butler."
    )


@router.get("/instruments", response_model=Config)
@router.get("/instruments/", response_model=Config, include_in_schema=False)
async def get_instruments(
    state: SharedState = fastapi.Depends(get_shared_state),
) -> Config:
    """Get the list of instruments."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, blocking_get_instruments, state.registries
    )


def blocking_get_instruments(
    registries: typing.Iterable[lsst.daf.butler.Registry],
) -> Config:
    instrument_lists = dict()
    for i, registry in enumerate(registries):
        instrument_lists[i] = [
            result.name
            for result in registry.queryDimensionRecords("instrument")
        ]

    return Config(
        butler_instruments_1=instrument_lists.get(0, []),
        butler_instruments_2=instrument_lists.get(1, []),
    )
