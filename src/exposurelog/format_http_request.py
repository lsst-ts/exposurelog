from __future__ import annotations

import datetime
import json
import typing

import astropy.time

from exposurelog.schemas.message_type import MessageType


def convert_item(key: str, value: typing.Any) -> typing.Any:
    """Convert a value into the form used by GraphQL."""
    if isinstance(value, tuple) or isinstance(value, list):
        formatted_items = [convert_item(key, item) for item in value]
        return f'[{", ".join(formatted_items)}]'
    if key.startswith("exposure_flag"):
        return value
    elif isinstance(value, str):
        # json forces double quotes around the string
        # and escapes special characters.
        return json.dumps(value)
    elif isinstance(value, datetime.datetime):
        return str(value)
    elif isinstance(value, astropy.time.Time):
        return value.tai.iso
    elif value is True:
        return "true"
    elif value is False:
        return "false"
    elif value is None:
        return "none"
    return str(value)


def format_http_request(
    category: str,
    command: str,
    args_dict: dict[str, typing.Any],
    fields: list[str] = None,
) -> tuple:
    """Format data for an exposure log GraphQL POST request.

    This is not sophisticated and is primarily intended for unit tests.
    It is specific to exposure log.
    For more general use consider using gqc, which has the ability
    to format requests.

    Parameters
    ----------
    category
        Message category; one of "query", "mutation", or "subscription".
    command
        Command, e.g. "add_message".
    args_dict
        Dict of argument name: data.
    fields
        Names of fields to return.
        If None then return all exposurelog message fields.

    Returns
    -------
    data_dict
        Data dict for the HTTP request.
    headers
        Dict of extra headers to prevent output of graphiql metadata.

    Notes
    -----
    Example of use::

        import requests

        from src.exposurelog.format_http_request import format_http_request

        url = "http://localhost:8000/exposurelog"
        find_args = dict(obs_id="HSCA90333600")
        find_data, headers = format_http_request(
            category="query", command="find_messages", args_dict=find_args
        )
        r = requests.post(url, find_data, headers=headers)
    """
    if category not in ("query", "mutation", "subscription"):
        raise ValueError(f"Unrecognized category {category}")
    if args_dict:
        basic_args_str = ",\n    ".join(
            f"{key}: {convert_item(key, value)}"
            for key, value in args_dict.items()
        )
        args_str = f"(\n    {basic_args_str}\n  ) "
    else:
        args_str = "\n  "
    if fields is None:
        fields = list(MessageType.fields)
    fields_str = "\n    ".join(fields)
    data_str = f"""
{category} {{
  {command}{args_str}{{
    {fields_str}
  }}
}}
"""
    return (
        dict(query=data_str),
        {"Accept": "application/json"},
    )
