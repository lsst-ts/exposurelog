###
owl
###

Observatory Wide Logbook (OWL) service

Create and manage log messages associated with a particular exposure.

Note that old messages are never deleted or modified,
other than the ``is_valid`` and ``date_is_valid_changed`` fields,
which support an approximation of deletion and modification.

owl is developed with the `Safir <https://safir.lsst.io>`__ framework.
`Get started with development with the tutorial <https://safir.lsst.io/set-up-from-template.html>`__.

Configuration
-------------

The following environment variables must be set in OWL's runtime environment.

* ``OWL_DATABASE_URL``: URL to the OWL message database, including username and password.
  Note that as of 2020-10 OWL only supports PostgreSQL message databases
  (because it uses asyncio and no other databases have a suitable driver).
* ``BUTLER_URI_1``: URI to an butler data repository, which is only read.
  Note that OWL only reads the registry, so the actual data files are optional.
* ``BUTLER_URI_2`` (optional): URI to a second, optional, data repository, which is searched after the first one.

The following environment variables may optionally be set to change default behavior.

* ``SAFIR_PROFILE``: Set to ``production`` to enable production logging
* ``SAFIR_LOG_LEVEL``: Set to ``DEBUG``, ``INFO``, ``WARNING``, or ``ERROR`` to change the log level.
  The default is ``INFO``.

Routes
------

* ``/``: Returns service metadata with a 200 status (used by Google Container Engine Ingress health check)

* ``/owl``: Returns metadata about the service.

* ``/owl/add``: Add a log message associated with a particular exposure.

* ``/owl/delete``: Delete a log message: set ``is_valid`` False and ``date_is_valid_changed`` to the current date.

* ``/owl/edit``: Edit a log message:

  * Find the old message.
  * Create a new message from the old data and the specified changes,
    with ``parent_id`` set to the ID of the old message.
  * In the old message set ``is_valid`` False and ``date_is_valid_changed`` to the current date. 
