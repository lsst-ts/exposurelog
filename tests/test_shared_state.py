from __future__ import annotations

import pathlib
import typing
import unittest

import asyncpg.exceptions
import testing.postgresql

from exposurelog.create_message_table import SITE_ID_LEN
from exposurelog.shared_state import (
    create_shared_state,
    delete_shared_state,
    get_env,
    get_shared_state,
    has_shared_state,
)
from exposurelog.testutils import (
    TEST_SITE_ID,
    create_test_database,
    db_config_from_dsn,
    modify_environ,
)


class SharedStateTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_shared_state(self) -> None:
        repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
        with testing.postgresql.Postgresql() as postgresql:
            try:
                await create_test_database(postgresql.url(), num_messages=0)
                assert not has_shared_state()
                with self.assertRaises(RuntimeError):
                    get_shared_state()

                required_kwargs: typing.Dict[str, typing.Any] = dict(
                    BUTLER_URI_1=str(repo_path),
                    SITE_ID=TEST_SITE_ID,
                )
                db_config = db_config_from_dsn(postgresql.dsn())

                # Dict of invalid database configuration and the expected error
                # that results if that one item is bad.
                db_bad_config_error = dict(
                    EXPOSURELOG_DB_PORT=("54321", OSError),
                    # An invalid EXPOSURELOG_DB_HOST takes a long time
                    # to time out, so don't bother.
                    EXPOSURELOG_DB_USER=(
                        "invalid_user",
                        asyncpg.exceptions.PostgresError,
                    ),
                    EXPOSURELOG_DB_DATABASE=(
                        "invalid_database",
                        asyncpg.exceptions.PostgresError,
                    ),
                )

                # Test missing required env variables.
                for key in required_kwargs:
                    missing_required_kwargs = required_kwargs.copy()
                    missing_required_kwargs[key] = None
                    with modify_environ(
                        **missing_required_kwargs,
                        **db_config,
                    ):
                        assert not has_shared_state()
                        with self.assertRaises(ValueError):
                            await create_shared_state()

                # Test invalid SITE_ID
                bad_site_id = "A" * (SITE_ID_LEN + 1)
                with modify_environ(
                    BUTLER_URI_1=str(repo_path),
                    SITE_ID=bad_site_id,
                    **db_config,
                ):
                    assert not has_shared_state()
                    with self.assertRaises(ValueError):
                        await create_shared_state()

                # Test invalid butler URI
                with modify_environ(
                    BUTLER_URI_1="bad/path/to/repo",
                    SITE_ID=TEST_SITE_ID,
                    **db_config,
                ):
                    assert not has_shared_state()
                    with self.assertRaises(FileNotFoundError):
                        await create_shared_state()

                # Test bad database configuration env variables.
                for key, (
                    bad_value,
                    expected_error,
                ) in db_bad_config_error.items():
                    bad_db_config = db_config.copy()
                    bad_db_config[key] = bad_value
                    with modify_environ(
                        **required_kwargs,
                        **bad_db_config,
                    ):
                        assert not has_shared_state()
                        with self.assertRaises(expected_error):
                            await create_shared_state()

                # Test a valid shared state
                with modify_environ(
                    **required_kwargs,
                    **db_config,
                ):
                    await create_shared_state()
                    assert has_shared_state()

                    state = get_shared_state()
                    assert len(state.registries) == 1
                    assert state.site_id == required_kwargs["SITE_ID"]

                    # Cannot create shared state once it is created
                    with self.assertRaises(RuntimeError):
                        await create_shared_state()

                await delete_shared_state()
                assert not has_shared_state()
                with self.assertRaises(RuntimeError):
                    get_shared_state()

                # Closing the database again should be a no-op
                await state.exposurelog_db.close()

                # Deleting shared state again should be a no-op
                await delete_shared_state()
                assert not has_shared_state()

                # Create two butler registries (both identical,
                # since we only have one).
                with modify_environ(
                    BUTLER_URI_2=str(repo_path),
                    **required_kwargs,
                    **db_config,
                ):
                    await create_shared_state()
                    assert has_shared_state()

                    shared_state = get_shared_state()
                    assert len(shared_state.registries) == 2
            finally:
                await delete_shared_state()

    def test_get_env(self) -> None:
        # If default=None then value must be present
        with modify_environ(SITE_ID=None):
            with self.assertRaises(ValueError):
                get_env(name="SITE_ID", default=None)

        # the default must be a str or None
        for bad_default in (1.2, 34, True, False):
            with self.assertRaises(ValueError):
                get_env(name="SITE_ID", default=bad_default)  # type: ignore
