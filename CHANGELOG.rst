==========
Change Log
==========

0.9.5
-----

* pyproject.toml: add PGUSER and PGPASSWORD to passenv.
* Update input and computed requirements.
* Apply dependabot alerts to .github/workflows/ci.yaml.

0.9.4
-----

* find_exposures:

    * Fix broken order_by handling (and possibly broken limit handling) and improve validation of the order_by order parameter.
    * Allow timespan_begin and timespan_end to be invalid (in which case they are set to None).
      Exposure ought to always have a valid timespan, but we have some that do not.

* find_messages: improve validation of the ``order_by`` query parameter.
* Update to python 3.10.
* Get daf_butler from pypi (as lsst-daf-butler) instead of github.
* Modernize type annotations, applying changes that required Python 3.9 or 3.10.
  Use native types or `collections.abc` where possible.
  Replace `typing.Union` and `typing.Optional` with ``|``.
  Remove ``from __future__ import annotations`` where possible.

0.9.3
-----

* Improve alembic migration to handle the case that the message table does not exist.
* Add ``tests/test_alembic_migration.py``.
* `LogMessageDatabase`: add message_table constructor argument to improve encapsulation.
* setup.cfg: specify asyncio_mode = auto.

0.9.2
-----

* Dockerfile was not copying the test repos.

0.9.1
-----

* Dockerfile: switch to a simpler base image, as per current SQuaRE recommendations.
* Add scripts/start-api.sh to run schema evolution and start the service.

0.9.0
-----

* Add support for schema evolution using alembic.
* Add "level" and "urls" columns to the message table.

0.8.0
-----

* Add a "tags" field to messages.
  Tags must be at least two letters long, contain only ASCII letters. digits, and _ (underscore), and start with a letter.
  Tags are transformed to lowercase.
* find_exposures: add ``registry``, ``offset``, and ``order_by`` parameters.
  It is no longer possible to search both registries at the same time,
  because that does not work well with ``order_by`` and ``offset``.
* Add get_instruments to show which instruments each butler registry supports.
* Work around a bug in the butler that made the service fail
  when run with two registries that contained data for different cameras.
* Replace the old test registry with two registries, each with data for a different camera.
* Include the raw images used to generate the registries (in a highly compressed form,
  with 0 for all pixel values) in order to simplify creating new versions of the registries.
* Add a hack to work around test failures on github: open Butlers with writeable=True when running tests.
  Undo this hack using DM-33642 once it's safe to do so.

0.7.1
-----

* Fix a bug in tests/test_find_messages.py: it could search for "\", which is not a valid search.
* Improve random seeding in unit tests.
* Use description instead of title for the metadata for returned objects.
  This improves the appearance of the interactive UI (especially redoc).

0.7.0
-----

Modernize the code:

* Update the specified and generated requirements.
* Use the ``main`` branch of ``daf_butler``, instead of ``master``.
* Fix some type annotations.
* For endpoints with an optional final "/" provide two endpoints: with and without the final "/".
  This fixes a new source of unit test breakage: uvicorn unexpectedly redirects.
  Hide the version with a final "/" from the API docs.
  Expand the unit tests to test both versions of each of these endpoints.
* Fix a new sqlachemy warning about empty ``and_`` clauses.

0.6.0
-----

* Support unicode in message text and enhance the tests to check it.
* delete messages/id: fix the declared status code.
  (It didn't cause problems, but it was confusing.)

0.5.1
-----

* Fix return value from deleting messages.
* Update generated requirements.

0.5.0
-----

* Allow searching for exposures.
* Enhance message search:

    * Make the "is_x" arguments tri-state, to expand the search options.
    * Document how to send array parameters.
