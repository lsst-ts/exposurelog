"""Externally-accessible endpoint handlers that serve
relative to ``/exposurelog/``.
"""

__all__ = ["get_index"]

from exposurelog.handlers.external.index import get_index
