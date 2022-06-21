Here are two butler registries one with LSSTComCam data and the other with LATISS data,
plus the files needed to recreate them.

* LATISS: a registry with metadata for some raw images
* LSSTCam: a registry with metadata for some raw images.
* raw_images: a directory of raw images used to create the LATISS and LSSTComcam registry.
  These images are highly compressed, with all pixel values zero.
  The LSSTCam images are from obs_lsst data/input/lsstCam/raw.
  The LATISS raw images are regular images, with image data zeroed using make_zeroed_fits_images.py.
* make_zeroed_fits_images.py: a command-line script that processes a directory of FITS images, zeroing and compressing the image data.

h2. How to create new registries

This is necessary whenever the registry format changes.

* Follow https://pipelines.lsst.io/v/weekly/index.html to install a recent DM software stack:

    * Install the lsst stack 
    * Install ``obs_lsst``
    * Run shebangatron: https://pipelines.lsst.io/v/weekly/index.html

* Run the following commands locally::

    setup obs_lsst

    butler create LSSTCam
    butler register-instrument LSSTCam lsst.obs.lsst.LsstCam
    butler ingest-raws LSSTCam raw_images/LSSTCam
    rm -rf LSSTCam/LSSTCam  # remove ingested images, to save space

    butler create LATISS
    butler register-instrument LATISS lsst.obs.lsst.Latiss
    butler ingest-raws LATISS raw_images/LATISS
    rm -rf LATISS/LATISS  # remove ingested images, to save space

h2. Registry contents

To show what is in the registries run::

    ./print_registry_contents.py

The results as of 2022-02-08:

registry=instrument=LSSTCam

id=3019032200002
exposure:
  instrument: 'LSSTCam'
  id: 3019032200002
  physical_filter: 'SDSSi~ND_OD0.5'
  obs_id: 'MC_C_20190322_000002'
  exposure_time: 1.0
  dark_time: 1.0
  observation_type: 'flat'
  observation_reason: 'flat'
  day_obs: 20190322
  seq_num: 2
  group_name: '3019032200002'
  group_id: 3019032200002
  target_name: 'UNKNOWN'
  science_program: '6489D'
  tracking_ra: None
  tracking_dec: None
  sky_angle: None
  zenith_angle: None
  timespan: Timespan(begin=astropy.time.Time('2019-03-22 15:31:01.904003', scale='tai', format='iso'), end=astropy.time.Time('2019-03-22 15:31:02.904003', scale='tai', format='iso'))
id=3019031900001
exposure:
  instrument: 'LSSTCam'
  id: 3019031900001
  physical_filter: 'unknown'
  obs_id: 'MC_C_20190319_000001'
  exposure_time: 0.0
  dark_time: 0.0
  observation_type: 'bias'
  observation_reason: 'bias'
  day_obs: 20190319
  seq_num: 1
  group_name: '3019031900001'
  group_id: 3019031900001
  target_name: 'UNKNOWN'
  science_program: 'unknown'
  tracking_ra: None
  tracking_dec: None
  sky_angle: None
  zenith_angle: None
  timespan: Timespan(begin=astropy.time.Time('2019-03-19 15:50:28.144991', scale='tai', format='iso'), end=astropy.time.Time('2019-03-19 15:50:28.144991', scale='tai', format='iso'))

registry=instrument=LATISS

id=2022020800143
exposure:
  instrument: 'LATISS'
  id: 2022020800143
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000143'
  exposure_time: 20.0
  dark_time: 20.3124952316284
  observation_type: 'engtest'
  observation_reason: 'intra'
  day_obs: 20220208
  seq_num: 143
  group_name: '2022-02-09T00:55:40.390'
  group_id: 2242977403900000
  target_name: 'HD  49790'
  science_program: 'CWFS'
  tracking_ra: 102.278392749663
  tracking_dec: -26.0644757888448
  sky_angle: 188.807815914692
  zenith_angle: 17.238877506650198
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 01:00:57.769401', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 01:01:17.994000', scale='tai', format='iso'))
id=2022020800151
exposure:
  instrument: 'LATISS'
  id: 2022020800151
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000151'
  exposure_time: 2.0
  dark_time: 2.3238422870636
  observation_type: 'science'
  observation_reason: 'object'
  day_obs: 20220208
  seq_num: 151
  group_name: '2022-02-09T01:18:55.093'
  group_id: 2242991350930000
  target_name: 'HD  49790'
  science_program: 'unknown'
  tracking_ra: 102.292270913397
  tracking_dec: -26.0716852179844
  sky_angle: 338.230071571806
  zenith_angle: 13.0822559611115
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 01:20:39.641249', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 01:20:41.876000', scale='tai', format='iso'))
id=2022020800145
exposure:
  instrument: 'LATISS'
  id: 2022020800145
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000145'
  exposure_time: 20.0
  dark_time: 20.320939540863
  observation_type: 'engtest'
  observation_reason: 'intra'
  day_obs: 20220208
  seq_num: 145
  group_name: '2022-02-09T00:55:40.390'
  group_id: 2242977403900000
  target_name: 'HD  49790'
  science_program: 'CWFS'
  tracking_ra: 102.278418936765
  tracking_dec: -26.0644835106208
  sky_angle: 188.807722490779
  zenith_angle: 16.917897106803096
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 01:02:29.059020', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 01:02:49.292000', scale='tai', format='iso'))
id=2022020800150
exposure:
  instrument: 'LATISS'
  id: 2022020800150
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000150'
  exposure_time: 2.0
  dark_time: 2.32216858863831
  observation_type: 'science'
  observation_reason: 'object'
  day_obs: 20220208
  seq_num: 150
  group_name: '2022-02-09T01:18:55.093'
  group_id: 2242991350930000
  target_name: 'HD  49790'
  science_program: 'unknown'
  tracking_ra: 102.292177163303
  tracking_dec: -26.0716890225194
  sky_angle: 338.23018514822
  zenith_angle: 13.158955963066504
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 01:20:17.809048', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 01:20:20.041000', scale='tai', format='iso'))
id=2022020800144
exposure:
  instrument: 'LATISS'
  id: 2022020800144
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000144'
  exposure_time: 20.0
  dark_time: 20.3223984241486
  observation_type: 'engtest'
  observation_reason: 'extra'
  day_obs: 20220208
  seq_num: 144
  group_name: '2022-02-09T00:55:40.390'
  group_id: 2242977403900000
  target_name: 'HD  49790'
  science_program: 'CWFS'
  tracking_ra: 102.278389105931
  tracking_dec: -26.0645115042018
  sky_angle: 188.807943149402
  zenith_angle: 17.139081896937597
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 01:01:25.365043', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 01:01:45.600000', scale='tai', format='iso'))
id=2022020800140
exposure:
  instrument: 'LATISS'
  id: 2022020800140
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000140'
  exposure_time: 20.0
  dark_time: 20.3281297683716
  observation_type: 'engtest'
  observation_reason: 'extra'
  day_obs: 20220208
  seq_num: 140
  group_name: '2022-02-09T00:55:40.390'
  group_id: 2242977403900000
  target_name: 'HD  49790'
  science_program: 'CWFS'
  tracking_ra: 102.278403320713
  tracking_dec: -26.0644886120432
  sky_angle: 188.807925992927
  zenith_angle: 17.8048343376431
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 00:58:20.135919', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 00:58:40.376000', scale='tai', format='iso'))
id=2022020800146
exposure:
  instrument: 'LATISS'
  id: 2022020800146
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000146'
  exposure_time: 20.0
  dark_time: 20.3202803134918
  observation_type: 'engtest'
  observation_reason: 'extra'
  day_obs: 20220208
  seq_num: 146
  group_name: '2022-02-09T00:55:40.390'
  group_id: 2242977403900000
  target_name: 'HD  49790'
  science_program: 'CWFS'
  tracking_ra: 102.278455280663
  tracking_dec: -26.0645015139504
  sky_angle: 188.80799621224
  zenith_angle: 16.8182458893571
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 01:02:56.522201', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 01:03:16.754000', scale='tai', format='iso'))
id=2022020800141
exposure:
  instrument: 'LATISS'
  id: 2022020800141
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000141'
  exposure_time: 20.0
  dark_time: 20.3068284988403
  observation_type: 'engtest'
  observation_reason: 'intra'
  day_obs: 20220208
  seq_num: 141
  group_name: '2022-02-09T00:55:40.390'
  group_id: 2242977403900000
  target_name: 'HD  49790'
  science_program: 'CWFS'
  tracking_ra: 102.278442397096
  tracking_dec: -26.0644740430966
  sky_angle: 188.807774418037
  zenith_angle: 17.567448110989105
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 00:59:25.629547', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 00:59:45.857000', scale='tai', format='iso'))
id=2022020800142
exposure:
  instrument: 'LATISS'
  id: 2022020800142
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000142'
  exposure_time: 20.0
  dark_time: 20.3248097896576
  observation_type: 'engtest'
  observation_reason: 'extra'
  day_obs: 20220208
  seq_num: 142
  group_name: '2022-02-09T00:55:40.390'
  group_id: 2242977403900000
  target_name: 'HD  49790'
  science_program: 'CWFS'
  tracking_ra: 102.27839886926
  tracking_dec: -26.0644956930385
  sky_angle: 188.80796173635
  zenith_angle: 17.467521073034703
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 00:59:54.046136', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 01:00:14.283000', scale='tai', format='iso'))
id=2022020800147
exposure:
  instrument: 'LATISS'
  id: 2022020800147
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000147'
  exposure_time: 5.0
  dark_time: 5.3159806728363
  observation_type: 'science'
  observation_reason: 'final'
  day_obs: 20220208
  seq_num: 147
  group_name: '2022-02-09T00:55:40.390'
  group_id: 2242977403900000
  target_name: 'HD  49790'
  science_program: 'CWFS'
  tracking_ra: 102.278419655072
  tracking_dec: -26.0644911086465
  sky_angle: 188.807788496204
  zenith_angle: 16.585606278589694
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 01:04:02.102938', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 01:04:07.331000', scale='tai', format='iso'))
id=2022020800148
exposure:
  instrument: 'LATISS'
  id: 2022020800148
  physical_filter: 'SDSSg~ronchi170lpmm'
  obs_id: 'AT_O_20220208_000148'
  exposure_time: 2.0
  dark_time: 2.31894087791443
  observation_type: 'science'
  observation_reason: 'object'
  day_obs: 20220208
  seq_num: 148
  group_name: '2022-02-09T01:15:40.129'
  group_id: 2242989401290000
  target_name: 'HD  49790'
  science_program: 'unknown'
  tracking_ra: 102.278466428031
  tracking_dec: -26.0645025436949
  sky_angle: 338.983127195963
  zenith_angle: 13.926996232679798
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 01:16:34.998084', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 01:16:37.229000', scale='tai', format='iso'))
id=2022020800149
exposure:
  instrument: 'LATISS'
  id: 2022020800149
  physical_filter: 'SDSSg~empty'
  obs_id: 'AT_O_20220208_000149'
  exposure_time: 2.0
  dark_time: 2.32207775115967
  observation_type: 'science'
  observation_reason: 'object'
  day_obs: 20220208
  seq_num: 149
  group_name: '2022-02-09T01:18:55.093'
  group_id: 2242991350930000
  target_name: 'HD  49790'
  science_program: 'unknown'
  tracking_ra: 102.278528804567
  tracking_dec: -26.0645224922972
  sky_angle: 338.229952825324
  zenith_angle: 13.247972221783101
  timespan: Timespan(begin=astropy.time.Time('2022-02-09 01:19:49.909789', scale='tai', format='iso'), end=astropy.time.Time('2022-02-09 01:19:52.143000', scale='tai', format='iso'))
