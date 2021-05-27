__all__ = ["Exposure"]

import datetime
import typing

import pydantic


class Exposure(pydantic.BaseModel):
    obs_id: str = pydantic.Field(title="Observation ID.")
    instrument: str = pydantic.Field(
        title="Short name of instrument, e.g. HSC."
    )
    observation_type: str = pydantic.Field(
        title="The observation type of this exposure "
        "(e.g. dark, bias, science)."
    )
    observation_reason: str = pydantic.Field(
        title="The reason this observation was taken. "
        "(e.g. science, filter scan, unknown)."
    )
    day_obs: int = pydantic.Field(title="Observation day.")
    seq_num: int = pydantic.Field(
        title="Counter for the observation within a larger sequence. "
        "Context of the sequence number is observatory specific. "
        "Can be a global counter or counter within day_obs."
    )
    group_name: str = pydantic.Field(
        title="String group identifier associated with this exposure "
        "by the acquisition system."
    )
    target_name: str = pydantic.Field(
        title="Object of interest for this observation or survey field name."
    )
    science_program: str = pydantic.Field(
        title="Observing program (survey, proposal, engineering project)."
    )
    tracking_ra: typing.Optional[float] = pydantic.Field(
        None,
        title="Tracking ICRS right ascension of boresight in degrees. "
        "Can be None for observations that are not on sky.",
    )
    tracking_dec: typing.Optional[float] = pydantic.Field(
        None,
        title="Tracking ICRS declination of boresight in degrees. "
        "Can be None for observations that are not on sky.",
    )
    sky_angle: typing.Optional[float] = pydantic.Field(
        None,
        title="Angle of the instrument focal plane on the sky in degrees. "
        "Can  be NULL for observations that are not on sky, or for "
        "where the sky angle changes during the observation.",
    )
    timespan_begin: datetime.datetime = pydantic.Field(
        title="Start TAI time of observation."
    )
    timespan_end: datetime.datetime = pydantic.Field(
        title="End TAI time of observation."
    )
