from __future__ import annotations

import itertools
import pathlib
import typing

import numpy as np
import testing.postgresql

from owl.app import create_app
from owl.schemas.message_type import MessageType
from owl.testutils import (
    MessageDictT,
    Requestor,
    assert_good_response,
    create_test_database,
)

if typing.TYPE_CHECKING:
    import aiohttp
    from aiohttp.pytest_plugin.test_utils import TestClient

random = np.random.RandomState(820)


class doc_str:
    """Decorator to add a doc string to a function.

    Unlike the standard technique, this works with f strings
    """

    def __init__(self, doc: str):
        self.doc = doc

    def __call__(self, func: typing.Callable) -> typing.Callable:
        func.__doc__ = self.doc
        return func


async def assert_good_find_response(
    response: aiohttp.ClientResponse,
    messages: typing.List[MessageDictT],
    predicate: typing.Callable,
) -> typing.List[MessageDictT]:
    """Assert that the correct messages were found.

    Parameters
    ----------
    response
        Response from find_messages command.
    messages
        All messages in the database (in any order).
    predicate
        Callable that takes one message and returns True if a message
        meets the find criteria, False if not.

    Returns
    found_messages
        The found messages.
    """
    found_messages = await assert_good_response(
        response, command="find_messages"
    )
    for message in found_messages:
        assert predicate(
            message
        ), f"message {message} does not match {predicate.__doc__}"
    missing_messages = get_missing_message(messages, found_messages)
    for message in missing_messages:
        assert not predicate(
            message
        ), f"message {message} matches {predicate.__doc__}"
    return found_messages


def assert_messages_ordered(
    messages: typing.List[MessageDictT], order_by: typing.List[str]
) -> None:
    """Assert that a list of message is ordered as specified.

    Parameters
    ----------
    messages
        Messages to test
    order_by
        Field names by which the data should be ordered.
        Each name can be prefixed by "-" to mean descending order.
    """
    message1 = None
    for message2 in messages:
        if message1 is not None:
            assert_two_messages_ordered(  # type: ignore
                message1,
                message2,
                order_by,
            )
        message1 = message2


def assert_two_messages_ordered(
    message1: MessageDictT, message2: MessageDictT, order_by: typing.List[str]
) -> None:
    """Assert that two messages are ordered as specified.

    Parameters
    ----------
    message1
        A message.
    message2
        The next message.
    order_by
        Field names by which the data should be ordered.
        Each name can be prefixed by "-" to mean descending order.
    """
    for key in order_by:
        if key.startswith("-"):
            field = key[1:]
            val1 = message1[field]
            val2 = message2[field]
            desired_cmp_result = 1
        else:
            field = key
            desired_cmp_result = -1
        val1 = message1[field]
        val2 = message2[field]
        cmp_result = cmp_message_field(field, val1, val2)
        if cmp_result == desired_cmp_result:
            # These two messages are fine
            return
        elif cmp_result != 0:
            raise AssertionError(
                f"messages mis-ordered in key {key}: "
                f"message1[{field}]={val1!r}, message2[{field}]={val2!r}"
            )


def cmp_message_field(field: str, val1: typing.Any, val2: typing.Any) -> int:
    """Return -1 if val1 < val2, 0 if val1 == val2, 1 if val1 > val2.

    Value None is equal to None and larger than every value.
    This mimics how PostgreSQL handles NULL.
    Field exposure_flag is ordered by enum.
    """
    if field == "exposure_flag":
        ordered_flag_values = dict(
            none="0: none", junk="1: junk", questionable="2: questionable"
        )
        val1 = ordered_flag_values[val1]
        val2 = ordered_flag_values[val2]
    if val1 == val2:
        return 0
    elif val1 is None:
        return 1
    elif val2 is None:
        return -1
    elif val1 > val2:
        return 1
    return -1


def get_missing_message(
    messages: typing.List[MessageDictT],
    found_messages: typing.List[MessageDictT],
) -> typing.List[MessageDictT]:
    """Get messages that were not found."""
    found_ids = set(found_message["id"] for found_message in found_messages)
    return [message for message in messages if message["id"] not in found_ids]


async def test_find_messages(aiohttp_client: TestClient) -> None:
    """Test adding a message."""
    repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
    num_messages = 12
    num_edited = 6  # Must be at least 4 in order to test ranges.
    with testing.postgresql.Postgresql() as postgresql:
        messages = create_test_database(
            postgresql=postgresql,
            num_messages=num_messages,
            num_edited=num_edited,
        )

        app = create_app(
            owl_database_url=postgresql.url(), butler_uri_1=repo_path
        )
        name = app["safir/config"].name

        client = await aiohttp_client(app)
        await app["owl/owl_database"].start_task

        requestor = Requestor(
            client=client,
            category="query",
            command="find_messages",
            url_suffix=f"{name}/graphql",
        )

        # Make predicates to test
        find_args_predicates = list()

        # Range arguments: min_<field>, max_<field>.
        for field in (
            "id",
            "day_obs",
            "date_added",
            "date_is_valid_changed",
            "parent_id",
        ):
            values = sorted(
                message[field]
                for message in messages
                if message[field] is not None
            )
            assert len(values) >= 4, f"not enough values for {field}"
            min_name = f"min_{field}"
            max_name = f"max_{field}"
            min_value = values[1]
            max_value = values[-1]
            assert max_value > min_value

            @doc_str(f"message[{field}] not None and >= {min_value}.")
            def test_min(
                message: MessageDictT,
                field: str = field,
                min_value: typing.Any = min_value,
            ) -> bool:
                return (
                    message[field] is not None and message[field] >= min_value
                )

            @doc_str(f"message[{field}] not None and < {max_value}.")
            def test_max(
                message: MessageDictT,
                field: str = field,
                max_value: typing.Any = max_value,
            ) -> bool:
                return (
                    message[field] is not None and message[field] < max_value
                )

            find_args_predicates += [
                ({min_name: min_value}, test_min),
                ({max_name: max_value}, test_max),
            ]

            if field == "day_obs":
                # Save these find args for later use
                find_args_day_obs = find_args_predicates[0][0]

            # Test that an empty range (max <= min) returns no messages.
            # There is no point combining this with other tests,
            # so test it now instead of adding it to find_args_predicates.
            response = await requestor(
                {min_name: min_value, max_name: min_value}
            )
            found_messages = await assert_good_response(
                response, command="find_messages"
            )
            assert len(found_messages) == 0

        # Collection arguments: <field>s, with a list of allowed values.
        num_to_find = 2
        for field in ("instrument", "user_id", "user_agent", "exposure_flag"):
            messages_to_find = random.choice(
                messages, size=num_to_find, replace=False
            )
            values = [message[field] for message in messages_to_find]

            @doc_str(f"message[{field}] in {values}")
            def test_collection(
                message: MessageDictT,
                field: str = field,
                values: typing.List[typing.Any] = values,
            ) -> bool:
                return message[field] in values

            find_args_predicates.append(
                ({f"{field}s": values}, test_collection)
            )

        # "Contains" arguments: these specify a substring to match.
        # Search for two characters out of one message,
        # in hopes more than one (though one is fine)
        # and fewer than all messages (not a good test)
        # will match.
        for field in ("obs_id", "message_text"):
            value = messages[2][field][1:2]

            @doc_str(f"{value} in message[{field}]")
            def test_contains(
                message: MessageDictT, field: str = field, value: str = value
            ) -> bool:
                return value in message[field]

            find_args_predicates.append(({field: value}, test_contains))

        # has_<field> arguments (for fields that may be null).
        for field in ("date_is_valid_changed", "parent_id"):
            arg_name = f"has_{field}"

            @doc_str(f"message[{field}] is not None")
            def test_has(message: MessageDictT, field: str = field) -> bool:
                return message[field] is not None

            @doc_str(f"message[{field}] is None")
            def test_has_not(
                message: MessageDictT, field: str = field
            ) -> bool:
                return message[field] is None

            find_args_predicates += [
                ({arg_name: True}, test_has),
                ({arg_name: False}, test_has_not),
            ]

        # Booleans fields.
        for field in ("is_human", "is_valid"):

            @doc_str(f"message[{field}] is True")
            def test_true(message: MessageDictT, field: str = field) -> bool:
                return message[field] is True

            @doc_str(f"message[{field}] is False")
            def test_false(message: MessageDictT, field: str = field) -> bool:
                return message[field] is False

            find_args_predicates += [
                ({field: True}, test_true),
                ({field: False}, test_false),
            ]

        # Test single requests: one entry from find_args_predicates.
        for find_args, predicate in find_args_predicates:
            response = await requestor(find_args)
            await assert_good_find_response(response, messages, predicate)

        # Test pairs of requests: two entries from find_args_predicates,
        # which are ``and``-ed together.
        for (
            (find_args1, predicate1),
            (find_args2, predicate2),
        ) in itertools.product(find_args_predicates, find_args_predicates):
            find_args = find_args1.copy()
            find_args.update(find_args2)
            if len(find_args) < len(find_args1) + len(find_args):
                # Overlapping arguments makes the predicates invalid.
                continue

            @doc_str(f"{predicate1.__doc__} and {predicate2.__doc__}")
            def and_predicates(
                message: MessageDictT,
                predicate1: typing.Callable,
                predicate2: typing.Callable,
            ) -> bool:
                return predicate1(message) and predicate2(message)

            response = await requestor(find_args)
            await assert_good_find_response(response, messages, and_predicates)

        # Test that find with no arguments finds all messages.
        response = await requestor(dict())
        messages = await assert_good_response(
            response, command="find_messages"
        )
        assert len(messages) == num_messages

        # Check order_by one field
        # Note: SQL databases sort strings differently than Python.
        # Rather than try to mimic Postgresql's sorting in Python,
        # I issue the order_by command but do not test the resulting
        # order if ordering by a string field.
        fields = list(MessageType.fields)
        str_fields = set(("instrument", "message_text", "obs_id"))
        for field in fields:
            order_by = [field]
            find_args = find_args_day_obs.copy()
            find_args["order_by"] = order_by
            response = await requestor(find_args)
            messages = await assert_good_response(
                response, command="find_messages"
            )
            if field not in str_fields:
                assert_messages_ordered(messages=messages, order_by=order_by)

        # Check order_by two fields
        for field1, field2 in itertools.product(fields, fields):
            order_by = [field1, field2]
            find_args = find_args_day_obs.copy()
            find_args["order_by"] = order_by
            response = await requestor(find_args)
            messages = await assert_good_response(
                response, command="find_messages"
            )
            if field1 not in str_fields and field2 not in str_fields:
                assert_messages_ordered(messages=messages, order_by=order_by)
