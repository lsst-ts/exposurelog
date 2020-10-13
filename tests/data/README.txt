hsc_raw was generated as follows:

* Start with a copy of the DM stack that includes obs_subaru
* git clone testdata_ci_hsc
$ setup obs_subaru
$ butler create hsc_raw
$ butler register-instrument hsc_raw lsst.obs.subaru.HyperSuprimeCam
$ butler ingest-raws hsc_raw <path_to_testdata_ci_hsc>/raw

Then delete all contents from hsc_raw except butler.yaml and gen3.sqlite3.
