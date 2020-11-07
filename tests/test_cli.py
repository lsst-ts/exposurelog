from __future__ import annotations

import asyncio
import os
import pathlib
import shutil
import subprocess
from typing import Optional

import pytest
import requests
import sqlalchemy as sa
import testing.postgresql

from explog.format_http_request import format_http_request

# Time limit for `explog create-table` (sec).
CREATE_TIMEOUT = 5

# Time limit for terminating a process (sec).
TERMINATE_TIMEOUT = 5

# Time to pause after executing `explog run` before trying to use it (sec).
RUN_DELAY = 2


@pytest.mark.asyncio
async def test_cli() -> None:
    """Test explog create-table and run command-line commands."""
    repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
    os.environ["BUTLER_URI_1"] = str(repo_path)

    exe_path = shutil.which("explog")
    assert (
        exe_path is not None
    ), "Could not find 'explog' bin script; you must build this package"

    with testing.postgresql.Postgresql() as postgresql:
        os.environ["EXPOSURE_LOG_DATABASE_URL"] = postgresql.url()
        engine = sa.create_engine(postgresql.url())

        create_table_process = await asyncio.create_subprocess_exec(
            "explog",
            "create-table",
            stderr=subprocess.PIPE,
        )

        await asyncio.wait_for(
            create_table_process.wait(), timeout=CREATE_TIMEOUT
        )
        data = await create_table_process.stderr.read()  # type: ignore
        assert (
            create_table_process.returncode == 0
        ), f"explog create-table failed with {data.decode()!r}"

        table_names = sa.inspect(engine).get_table_names()
        assert "exposure_log_messages" in table_names

        # Check `explog run` with and without the --port argument
        for port, message_id in ((None, 1), (8001, 2)):
            await check_run_and_add_message(port=port, message_id=message_id)


async def check_run_and_add_message(
    port: Optional[int], message_id: int
) -> None:
    """Run `explog run` and use it to add one message.

    Before calling this you must have a database running.

    Parameters
    ----------
    port
        Port on which to run the explog service. If None then run without
        specifying a port, which uses the default port 8080.
    message_id
        Expected ID of the added message.
    """

    cmdline_args = ["explog", "run"]
    if port is None:
        port = 8080
    else:
        cmdline_args += ["--port", str(port)]

    run_process = await asyncio.create_subprocess_exec(
        *cmdline_args,
        stderr=subprocess.PIPE,
    )
    try:

        # Give the exposure log service time to start.
        await asyncio.sleep(RUN_DELAY)

        # Add a message whose obs_id matches an exposure.
        add_args = dict(
            obs_id="HSCA90333600",
            instrument="HSC",
            message_text="A sample message",
            user_id="test_add_message",
            user_agent="pytest",
            is_human=False,
            is_new=False,
            exposure_flag="none",
        )
        add_data, headers = format_http_request(
            category="mutation",
            command="add_message",
            args_dict=add_args,
            fields=["id"],
        )
        r = requests.post(
            f"http://localhost:{port}/explog/graphql",
            add_data,
            headers=headers,
        )
        assert r.status_code == 200
        reply_data = r.json()
        assert "error" not in reply_data
        assert reply_data["data"]["add_message"]["id"] == message_id

    finally:
        if run_process.returncode is None:
            # `explog run` is still running, as it should be. Stop it.
            run_process.terminate()
            await asyncio.wait_for(
                run_process.wait(), timeout=TERMINATE_TIMEOUT
            )
        else:
            # The `explog run` process unexpectedly quit.
            # This would likely cause other test failures.
            # so report process termination instead of any other errors.
            # Try to include stderr from the process in the error message.
            try:
                stderr_bytes = await run_process.stderr.read()  # type: ignore
                stderr_msg = stderr_bytes.decode()
            except Exception as e:
                stderr_msg = f"could not read stderr: {e}"
            raise AssertionError(f"run_process failed: {stderr_msg}")
