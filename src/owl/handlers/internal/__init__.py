"""Internal HTTP handlers that serve relative to the root path, ``/``.

These handlers aren't externally visible since the app is available at a path,
``/owl``. See `owl.handlers.external` for
the external endpoint handlers.
"""

__all__ = ["get_index"]

from owl.handlers.internal.index import get_index
