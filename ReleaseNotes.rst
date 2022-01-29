=============
Release Notes
=============

0.6.0
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
