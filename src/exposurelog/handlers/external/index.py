"""Handler for the app's external root, ``/exposurelog/``."""

__all__ = ["get_index"]

from aiohttp import web

from exposurelog.handlers import routes


@routes.get("/")
async def get_index(request: web.Request) -> web.Response:
    """GET /exposurelog/ (the app's external root).

    By convention, the root of the external API includes a field called
    ``_metadata`` that provides the same metadata as the internal root
    endpoint. Here, the metadata is a namespace so that you can customize the
    root of your API. For example, consider listing key API URLs.
    """
    metadata = request.config_dict["safir/metadata"]
    data = {"_metadata": metadata}

    return web.json_response(data)
