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
All are optional except the ones marked "required":

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

Routes
------

* ``/``: Returns service metadata with a 200 status (used by Google Container Engine Ingress health check)

* ``/exposurelog``: The Exposure Log service.
