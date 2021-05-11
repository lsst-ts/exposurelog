__all__ = ["ExposureFlag", "Message", "MESSAGE_FIELDS"]

import datetime
import enum
import typing
import uuid

import pydantic


class ExposureFlag(str, enum.Enum):
    none = "none"
    junk = "junk"
    questionable = "questionable"


class Message(pydantic.BaseModel):
    id: uuid.UUID = pydantic.Field(
        title="Message ID: a UUID that is the primary key."
    )
    site_id: str = pydantic.Field(
        title="Site at which the message was created."
    )
    obs_id: str = pydantic.Field(title="Observation ID.")
    instrument: str = pydantic.Field(
        title="Short name of instrument, e.g. HSC."
    )
    day_obs: int = pydantic.Field(title="Observation day.")
    message_text: str = pydantic.Field(title="Message.")
    user_id: str = pydantic.Field(title="User ID.")
    user_agent: str = pydantic.Field(
        title="User agent: the application that created the message."
    )
    is_human: bool = pydantic.Field(
        title="Was it a human who created the message?"
    )
    is_valid: bool = pydantic.Field(
        title="Is this message still valid (false if deleted or edited)."
    )
    exposure_flag: ExposureFlag = pydantic.Field(
        title="Flag indicating exposure may have problems."
    )
    date_added: datetime.datetime = pydantic.Field(
        title="TAI date at which the message was added."
    )
    date_invalidated: typing.Optional[datetime.datetime] = pydantic.Field(
        title="TAI date at which is_valid was last set true."
    )
    parent_id: typing.Optional[uuid.UUID] = pydantic.Field(
        title="Message ID of message this is an edited version of."
    )


MESSAGE_FIELDS = tuple(Message.schema()["properties"].keys())
