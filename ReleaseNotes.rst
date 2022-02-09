=============
Release Notes
=============

0.8.0
-----

* find_exposures: add ``registry``, ``offset``, and ``order_by`` parameters.
  Note that it is no longer possible to search both registries at the same time,
  because that does not play well with ``order_by`` and ``offset``.
* Add get_instruments to show which instruments each butler registry supports.
* Work around a bug in the butler that made the service fail
  when run with two registries that contained data for different cameras.
* Replace the old test registry with two registries, each with data for a different camera,
  in order to test the bug just mentioned.
* Include the raw images used to generate the registries (in a highly compressed form,
  with 0 for all pixel values) in order to simplify creating new versions of the registries.

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
