from __future__ import annotations

import fastapi
import fastapi.responses
import starlette.requests

from . import shared_state
from .routers import (
    add_message,
    delete_message,
    edit_message,
    find_exposures,
    find_messages,
    get_configuration,
    get_message,
)

app = fastapi.FastAPI()

subapp = fastapi.FastAPI(
    title="Exposure log service",
    description="A REST web service to create and manage log messages "
    "that are associated with a particular exposure.",
)
app.mount("/exposurelog", subapp)

subapp.include_router(add_message.router)
subapp.include_router(delete_message.router)
subapp.include_router(edit_message.router)
subapp.include_router(find_messages.router)
subapp.include_router(find_exposures.router)
subapp.include_router(get_configuration.router)
subapp.include_router(get_message.router)


@subapp.get("/", response_class=fastapi.responses.HTMLResponse)
async def root(request: starlette.requests.Request) -> str:
    return f"""<html>
    <head>
        <title>
            Exposure log service
        </title>
    </head>
    <body>
        <h1>Exposure log service</h1>

        <p>Create and manage log messages associated with exposures.</p>

        <p>OpenAPI documentation is available in two flavors:
        <a href="{request.url}redoc">redoc</a>, which is easy to read, and
        <a href="{request.url}docs">docs</a> (swagger), which is interactive,
        but harder to read.
    </html>
    """


@app.on_event("startup")
async def startup_event() -> None:
    await shared_state.create_shared_state()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await shared_state.delete_shared_state()
