hsc_raw was generated as follows:

* Start with a copy of the DM stack that includes obs_subaru
* git clone https://github.com/lsst/testdata_ci_hsc
* execute these commands::

    rm -rf hsc_raw
    setup obs_subaru
    setup -k testdata_ci_hsc
    butler create hsc_raw
    butler register-instrument hsc_raw lsst.obs.subaru.HyperSuprimeCam
    butler ingest-raws hsc_raw <path-to-testdata_ci_hsc>/raw

Then delete all contents from hsc_raw except butler.yaml and gen3.sqlite3.
