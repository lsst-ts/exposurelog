"""Internal HTTP handlers that serve relative to the root path, ``/``.

These handlers aren't externally visible since the app is available at path,
``/exposurelog``. See `exposurelog.handlers.external` for external endpoint
handlers.
"""

__all__ = ["get_index"]

from exposurelog.handlers.internal.index import get_index
