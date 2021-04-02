############
Exposure Log
############

Create and manage log messages associated with a particular exposure.

Note that old log messages are never deleted or modified,
other than the ``is_valid`` and ``date_is_valid_changed`` fields,
which support an approximation of deletion and modification.

Exposure Log is developed with the `Safir <https://safir.lsst.io>`__ framework.
`Get started with development with the tutorial <https://safir.lsst.io/set-up-from-template.html>`__.

Configuration
-------------

The following environment variables may be set in Exposure Log's runtime environment.
See the file ``config.py`` for details and default values.
All are optional except the ones marked "(required)":

* ``BUTLER_URI_1`` (required): URI to an butler data repository, which is only read.
  Note that Exposure Log only reads the registry, so the actual data files are optional.
* ``BUTLER_URI_2``: URI to a second, optional, data repository, which is searched after the first one.
* ``EXPOSURELOG_DB_USER``: Exposurelog database user name
* ``EXPOSURELOG_DB_PASSWORD`` (required): Exposurelog database password.
* ``EXPOSURELOG_DB_HOST`` (required): Exposurelog database server host.
* ``EXPOSURELOG_DB_PORT``: Exposurelog database server port.
* ``EXPOSURELOG_DB_DATABASE``: Exposurelog database name.
* ``SAFIR_PROFILE``: Set to ``production`` to enable production logging
* ``SAFIR_LOG_LEVEL``: Set to ``DEBUG``, ``INFO``, ``WARNING``, or ``ERROR`` to change the log level.
  The default is ``INFO``.
* ``SITE_ID``: Where this is deployed, e.g. "summit" or "ncsa".
  The value is part of the message primary key, to support synchronizing databases.

Routes
------

* ``/``: Returns service metadata with a 200 status (used by Google Container Engine Ingress health check)

* ``/exposurelog``: The Exposure Log service.

Developer Guide
---------------

Create (once) and activate a local conda environment::

  conda create --name square python=3.8
  conda env list

  conda activate square

If you change requirements (in requirements/dev.in or main.in) or if running the code gives a "package not found" error
update the generated dependencies and install the new requirements using::

  # It is an annoying bug that it has to be run twice
  # but if you only run it once then `lsst.utils` is not found.
  make update; make update

tox configuration goes in pyproject.toml (not tox.ini, as so many tox documents suggest).

To run tests (including code coverage, linting and typing)::

  tox

To lint the code (run it twice if it reports a linting error the first time)::

  tox -e lint

To check type annotation with mypy::

  tox -e typing

To run the service locally you will first need a running Postgres server with a user named ``exposurelog``.
See Postgres Guide for instructions. Once that is running::

  export BUTLER_URI_1=~/UW/LSST/tsrepos/exposurelog/tests/data/hsc_raw
  export SITE_ID="test"
  exposurelog run

  # Then open this link in a browser: http://localhost:8080/exposurelog

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
