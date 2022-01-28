from __future__ import annotations

import itertools
import pathlib
import typing
import unittest

import httpx
import lsst.daf.butler
import numpy as np

from exposurelog.routers.find_exposures import dict_from_exposure
from exposurelog.shared_state import get_shared_state
from exposurelog.testutils import (
    assert_good_response,
    cast_special,
    create_test_client,
)

ExposureDictT = typing.Dict[str, typing.Any]

random = np.random.RandomState(32)


class doc_str:
    """Decorator to add a doc string to a function.

    Unlike the standard technique, this works with f strings
    """

    def __init__(self, doc: str):
        self.doc = doc

    def __call__(self, func: typing.Callable) -> typing.Callable:
        func.__doc__ = self.doc
        return func


def assert_good_find_response(
    response: httpx.Response,
    exposures: list[ExposureDictT],
    predicate: typing.Callable,
) -> list[ExposureDictT]:
    """Assert that the correct exposures were found.

    Parameters
    ----------
    response
        Response from find_exposures command.
    exposures
        All exposures in the database (in any order).
    predicate
        Callable that takes one exposure and returns True if a exposure
        meets the find criteria, False if not.

    Returns
    found_exposures
        The found exposures.
    """
    found_exposures = assert_good_response(response)
    for exposure in found_exposures:
        assert predicate(
            exposure
        ), f"exposure {exposure} does not match {predicate.__doc__}"
    missing_exposures = get_missing_exposure(exposures, found_exposures)
    for exposure in missing_exposures:
        assert not predicate(
            exposure
        ), f"exposure {exposure} matches {predicate.__doc__}"
    return found_exposures


def get_range_values(
    exposures: list[ExposureDictT], field: str
) -> typing.Tuple[float, float]:
    values = sorted(exposure[field] for exposure in exposures)
    assert len(values) >= 4, f"not enough values for {field}"
    min_value = values[1]
    max_value = values[-1]
    assert max_value > min_value
    return min_value, max_value


def get_missing_exposure(
    exposures: list[ExposureDictT],
    found_exposures: list[ExposureDictT],
) -> list[ExposureDictT]:
    """Get exposures that were not found."""
    found_ids = set(
        found_exposure["obs_id"] for found_exposure in found_exposures
    )
    return [
        exposure
        for exposure in exposures
        if str(exposure["obs_id"]) not in found_ids
    ]


class FindExposuresTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_find_exposures(self) -> None:
        repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
        instrument = "HSC"

        # Find all exposures in the registry,
        # and save as a list of dicts
        butler = lsst.daf.butler.Butler(str(repo_path), writeable=False)
        registry = butler.registry
        exposure_iter = registry.queryDimensionRecords(
            "exposure",
            instrument=instrument,
        )
        exposures = [
            dict_from_exposure(exposure) for exposure in exposure_iter
        ]
        exposures.sort(key=lambda exposure: exposure["obs_id"])

        # Check for duplicate exposures
        obs_ids = {exposure["obs_id"] for exposure in exposures}
        assert len(obs_ids) == len(exposures)

        # Make sure we got some exposures -- enough to select a subset
        # and pick a subrange.
        assert len(exposures) > 5

        # Make sure all exposures have the right instrument
        for exposure in exposures:
            assert exposure["instrument"] == instrument

        async with create_test_client(repo_path=repo_path) as (
            client,
            messages,
        ):
            # Test that instrument is required
            response = await client.get(
                "/exposurelog/exposures",
                params={"limit": 1},
            )
            assert response.status_code == 422

            async def run_find(
                find_args: typing.Dict[str, typing.Any],
                instrument: str = instrument,
            ) -> httpx.Response:
                """Run a query after adding instrument parameter."""
                full_find_args = find_args.copy()
                full_find_args["instrument"] = instrument
                response = await client.get(
                    "/exposurelog/exposures",
                    params=full_find_args,
                )
                return response

            # Make a list of find arguments and associated predicates.
            # Each entry is a tuple of:
            # * dict of find arg name: value
            # * predicate: function that takes an exposure dict
            #   and returns True if the exposure matches the query
            find_args_predicates: typing.List[
                typing.Tuple[typing.Dict[str, typing.Any], typing.Callable]
            ] = list()

            # Range arguments: min_<field>, max_<field>
            # except min/max date, which is handled above.
            for field in ("day_obs", "seq_num", "date"):
                min_name = f"min_{field}"
                max_name = f"max_{field}"

                if field == "date":
                    # min_date and max_date need special handling
                    # because they are compared to a time span,
                    # rather than a scalar
                    min_field = "timespan_end"
                    max_field = "timespan_begin"
                    min_value, __ = get_range_values(
                        exposures=exposures, field=min_field
                    )
                    _, max_value = get_range_values(
                        exposures=exposures, field=max_field
                    )

                    @doc_str(f"exposure[{min_field!r}] > {min_value}.")
                    def test_min(
                        exposure: ExposureDictT,
                        field: str = min_field,
                        min_value: typing.Any = min_value,
                    ) -> bool:
                        min_value = cast_special(min_value)
                        value = cast_special(exposure[field])
                        return value > min_value

                    @doc_str(f"exposure[{max_field!r}] < {max_value}.")
                    def test_max(
                        exposure: ExposureDictT,
                        field: str = max_field,
                        max_value: typing.Any = max_value,
                    ) -> bool:
                        max_value = cast_special(max_value)
                        value = cast_special(exposure[field])
                        return value < max_value

                else:
                    min_field = field
                    max_field = field
                    min_value, max_value = get_range_values(
                        exposures=exposures, field=field
                    )

                    @doc_str(f"exposure[{min_field!r}] >= {min_value}.")
                    def test_min(
                        exposure: ExposureDictT,
                        field: str = min_field,
                        min_value: typing.Any = min_value,
                    ) -> bool:
                        min_value = cast_special(min_value)
                        value = cast_special(exposure[field])
                        return value >= min_value

                    @doc_str(f"exposure[{max_field!r}] < {max_value}.")
                    def test_max(
                        exposure: ExposureDictT,
                        field: str = max_field,
                        max_value: typing.Any = max_value,
                    ) -> bool:
                        max_value = cast_special(max_value)
                        value = cast_special(exposure[field])
                        return value < max_value

                find_args_predicates += [
                    ({min_name: min_value}, test_min),
                    ({max_name: max_value}, test_max),
                ]

                # Test that an empty range (max <= min) returns no exposures.
                # There is no point combining this with other tests,
                # so test it now instead of adding it to find_args_predicates.
                empty_range_args = {
                    min_name: min_value,
                    max_name: min_value,
                }
                response = await run_find(empty_range_args)
                found_exposures = assert_good_response(response)
                assert len(found_exposures) == 0

            # Collection arguments: <field>s, with a list of allowed values.
            num_to_find = 2
            for field in (
                "group_name",
                "observation_reason",
                "observation_type",
            ):
                exposures_to_find = random.choice(
                    exposures, size=num_to_find, replace=False
                )
                values = [exposure[field] for exposure in exposures_to_find]

                @doc_str(f"exposure[{field!r}] in {values}")
                def test_collection(
                    exposure: ExposureDictT,
                    field: str = field,
                    values: list[typing.Any] = values,
                ) -> bool:
                    return exposure[field] in values

                find_args_predicates.append(
                    ({f"{field}s": values}, test_collection)
                )

            # Test single requests: one entry from find_args_predicates.
            for find_args, predicate in find_args_predicates:
                response = await run_find(find_args)
                assert_good_find_response(response, exposures, predicate)

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
                    exposure: ExposureDictT,
                    predicate1: typing.Callable,
                    predicate2: typing.Callable,
                ) -> bool:
                    return predicate1(exposure) and predicate2(exposure)

                response = await run_find(find_args)
                assert_good_find_response(response, exposures, and_predicates)

            # Test that find with no arguments finds all exposures.
            response = await run_find(dict())
            assert_good_find_response(
                response, exposures, lambda exposure: True
            )

            # Test that limit limits the number of records
            for limit in (
                1,
                len(exposures) - 3,
                len(exposures),
                len(exposures) + 3,
            ):
                response = await run_find({"limit": limit})
                found_exposures = assert_good_response(response)
                assert len(found_exposures) == min(limit, len(exposures))
                found_obs_ids = {
                    exposure["obs_id"] for exposure in found_exposures
                }
                assert len(found_obs_ids) == len(found_exposures)
                assert found_obs_ids <= obs_ids

            # Test that limit must be positive
            response = await run_find({"limit": 0})
            assert response.status_code == 422

    async def test_duplicate_registries(self) -> None:
        """Test a server that has two repositories.

        Unfortunately I only have one test repo (and it's hard enough
        maintaining that as daf_butler evolves) so I just connect to it twice.
        """
        repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
        instrument = "HSC"

        # Find all exposures in the registry,
        # and save as a list of dicts
        butler = lsst.daf.butler.Butler(str(repo_path), writeable=False)
        registry = butler.registry
        exposure_iter = registry.queryDimensionRecords(
            "exposure",
            instrument=instrument,
        )
        exposures = [
            dict_from_exposure(exposure) for exposure in exposure_iter
        ]
        exposures.sort(key=lambda exposure: exposure["obs_id"])

        # Check for duplicate exposures.
        obs_ids = {exposure["obs_id"] for exposure in exposures}
        assert len(obs_ids) == len(exposures)

        async with create_test_client(
            repo_path=repo_path,
            repo_path_2=repo_path,
        ) as (
            client,
            messages,
        ):
            shared_state = get_shared_state()
            assert len(shared_state.registries) == 2

            async def run_find(
                find_args: typing.Dict[str, typing.Any],
                instrument: str = instrument,
            ) -> httpx.Response:
                """Run a query after adding instrument parameter."""
                full_find_args = find_args.copy()
                full_find_args["instrument"] = instrument
                response = await client.get(
                    "/exposurelog/exposures",
                    params=full_find_args,
                )
                return response

            response = await run_find({})
            found_exposures = assert_good_find_response(
                response, exposures, lambda exposure: True
            )
            found_obs_ids = {
                exposure["obs_id"] for exposure in found_exposures
            }
            assert len(found_obs_ids) == len(found_exposures)

            # Check for duplicate exposures when using limit.
            for limit in (
                1,
                len(exposures) - 3,
                len(exposures),
                len(exposures) + 3,
            ):
                response = await run_find({"limit": limit})
                found_exposures = assert_good_response(response)
                assert len(found_exposures) == min(limit, len(exposures))
                found_obs_ids = {
                    exposure["obs_id"] for exposure in found_exposures
                }
                assert len(found_obs_ids) == len(found_exposures)
                assert found_obs_ids <= obs_ids
