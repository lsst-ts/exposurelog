############
Exposure Log
############

Exposure log is a REST web service to create and manage log messages that are associated with a particular exposure.

The service runs at _address_:8080/exposurelog
and OpenAPI docs are available at _address_:8080/exposurelog/docs.

Messages are immutable, other than two fields: ``date_invalidated`` and ``is_valid``
(which is computed from ``date_invalidated``).
These fields provide a reasonable approximation of deletion and modification.

Configuration
-------------

The service is configured via the following environment variables;
All are optional except the few marked "(required)":

* ``SITE_ID`` (required): Where this is deployed. Standard values include "summit" and "base".
* ``BUTLER_URI_1`` (required): URI to an butler data repository, which is only read.
  Note that Exposure Log only reads the registry, so the actual data files are optional.
* ``BUTLER_URI_2``: URI to a second, optional, data repository, which is searched after the first one.
* ``EXPOSURELOG_DB_USER``: Exposurelog database user name: default="exposurelog".
* ``EXPOSURELOG_DB_PASSWORD``: Exposurelog database password; default="".
* ``EXPOSURELOG_DB_HOST``: Exposurelog database server host; default="localhost".
* ``EXPOSURELOG_DB_PORT``: Exposurelog database server port; default="5432".
* ``EXPOSURELOG_DB_DATABASE``: Exposurelog database name; default="exposurelog".

Developer Guide
---------------

Create (once) and activate a local conda environment::

  conda create --name square python=3.10
  conda env list

  conda activate square

For development work, you can install dependencies into the current conda environment,
and put the src directory in the PYTHONPATH using::

  make init
 
If you change requirements (in requirements/dev.in or main.in),
or if running the code gives a "package not found" error,
update the generated dependencies and install the new requirements using::

  make update-deps
  make update

tox configuration goes in pyproject.toml (not tox.ini, as tox documentation often suggests).

To run tests (including code coverage, linting and typing)::

  tox

If that fails with a complaint about missing packages try rebuilding your environment::

  tox -r

To lint the code, including type checking (run it twice if it reports a linting error the first time)::

  tox -e lint

To run the service, you will need a running Postgres server with a user named ``exposurelog``
that has permission to create tables and rows, and a database also named ``exposurelog``.
With the Postgres server running::

  # Configure the service
  export SITE_ID=test
  export BUTLER_URI_1=.../exposurelog/tests/data/LATISS
  # Also set EXPOSURELOG_DB_x environment variables as needed; see Configuration above

  # Start the service.
  # The default port is 8000, but the LSST standard port is 8080.
  # --reload will reload the source code when you change it (don't use for production).
  uvicorn exposurelog.main:app [--port n] [--reload]

  # If running the service locally on port 8000, connect to it at: http://localhost:8000/exposurelog/

Postgres Guide
--------------

This is a very basic guide focused on the exposurelog service.

To start postgres manually (in case you don't routinely leave it running)::

    pg_ctl -D /usr/local/var/postgres start

To stop postgres manually::

    pg_ctl -D /usr/local/var/postgres stop -s -m fast

To connect to the postgres server in order to create a new user or database::

    psql -U postgres -d postgres

To create the exposurelog user and database::

    CREATE USER exposurelog WITH CREATEDB;
    CREATE DATABASE exposurelog;

To connect as user exposurelog and use the exposurelog database (e.g. to see data or schema)::

    psql -U exposurelog -d exposurelog

List all databases::

    \l

Show the schema for the current table::

    \d
