from __future__ import annotations

import fastapi

from . import shared_state
from .routers import add_message, delete_messages, edit_message, find_messages

app = fastapi.FastAPI()

app.include_router(add_message.router)
app.include_router(delete_messages.router)
app.include_router(edit_message.router)
app.include_router(find_messages.router)


@app.get("/exposurelog")
async def root() -> dict:
    return dict(
        message="exposurelog: create and manage log messages "
        "associated with exposures. An OpenAPI service."
    )


@app.on_event("startup")
async def startup_event() -> None:
    await shared_state.create_shared_state()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await shared_state.delete_shared_state()
