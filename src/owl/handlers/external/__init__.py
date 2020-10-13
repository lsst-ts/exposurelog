"""Externally-accessible endpoint handlers that serve relative to
``/<app-name>/``.
"""

__all__ = ["add_message", "delete_message", "edit_message", "get_index"]

from owl.handlers.external.add import add_message
from owl.handlers.external.delete import delete_message
from owl.handlers.external.edit import edit_message
from owl.handlers.external.index import get_index
