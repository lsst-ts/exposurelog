__all__ = ["dict_from_result_proxy"]

import datetime

import sqlalchemy


def dict_from_result_proxy(result: sqlalchemy.engine.ResultProxy) -> dict:
    """Convert a ResultProxy to a dict, with timestamps as ISO time strings."""
    data_dict = dict()
    for key, value in result.items():
        if isinstance(value, datetime.datetime):
            data_dict[key] = str(value)
        else:
            data_dict[key] = value
    return data_dict
