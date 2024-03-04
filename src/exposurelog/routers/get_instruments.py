__all__ = ["get_instruments"]

import asyncio

import fastapi
import pydantic

from ..butler_factory import ButlerFactory
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()


class Config(pydantic.BaseModel):
    butler_instruments_1: list[str] = pydantic.Field(
        description="Instruments supported by butler 1."
    )
    butler_instruments_2: list[str] = pydantic.Field(
        description="Instruments supported by butler 2; "
        "'[]' if there is only one butler."
    )
    butler_instruments_3: list[str] = pydantic.Field(
        description="Instruments supported by butler 3; "
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
        None,
        blocking_get_instruments,
        state.butler_factory,
    )


def blocking_get_instruments(factory: ButlerFactory) -> Config:
    instrument_lists = dict()
    for i, butler in enumerate(factory.get_all_butlers()):
        instrument_lists[i] = [
            result.name
            for result in butler.registry.queryDimensionRecords("instrument")
        ]

    return Config(
        butler_instruments_1=instrument_lists.get(0, []),
        butler_instruments_2=instrument_lists.get(1, []),
        butler_instruments_3=instrument_lists.get(2, []),
    )
