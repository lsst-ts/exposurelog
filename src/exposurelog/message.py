__all__ = ["ExposureFlag", "Message", "MESSAGE_FIELDS"]

import datetime
import enum
import typing

import pydantic


class ExposureFlag(str, enum.Enum):
    none = "none"
    junk = "junk"
    questionable = "questionable"


class Message(pydantic.BaseModel):
    id: int = pydantic.Field(
        description="Message ID; an auto-incremented integer. "
        "Each message has a unique (id, site_id)."
    )
    site_id: str = pydantic.Field(
        description="Site at which the message was created."
    )
    obs_id: str = pydantic.Field(description="Observation ID.")
    instrument: str = pydantic.Field(
        description="Short name of instrument, e.g. HSC."
    )
    day_obs: int = pydantic.Field(description="Observation day.")
    message_text: str = pydantic.Field(description="Message.")
    user_id: str = pydantic.Field(description="User ID.")
    user_agent: str = pydantic.Field(
        description="User agent: the application that created the message."
    )
    is_human: bool = pydantic.Field(
        description="Was it a human who created the message?"
    )
    is_valid: bool = pydantic.Field(
        description="Is this message still valid (false if deleted or edited)."
    )
    exposure_flag: ExposureFlag = pydantic.Field(
        description="Flag indicating exposure may have problems."
    )
    date_added: datetime.datetime = pydantic.Field(
        description="TAI date at which the message was added."
    )
    date_is_valid_changed: typing.Optional[datetime.datetime] = pydantic.Field(
        description="TAI date at which is_valid was last set true."
    )
    parent_id: typing.Optional[int] = pydantic.Field(
        description="Message ID of message this is an edited version of."
    )
    parent_site_id: typing.Optional[str] = pydantic.Field(
        description="Site ID of message this is an edited version of."
    )


MESSAGE_FIELDS = tuple(Message.schema()["properties"].keys())
