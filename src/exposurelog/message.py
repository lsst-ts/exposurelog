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
        description="Message ID: a UUID that is the primary key."
    )
    site_id: str = pydantic.Field(
        description="Site at which the message was created."
    )
    obs_id: str = pydantic.Field(description="Observation ID.")
    instrument: str = pydantic.Field(
        description="Short name of instrument, e.g. LSSTCam."
    )
    day_obs: int = pydantic.Field(description="Observation day.")
    message_text: str = pydantic.Field(description="Message.")
    level: int = pydantic.Field(
        title="Message level. A python logging level: "
        "info=20, warning=30, error=40."
    )
    tags: typing.List[str] = pydantic.Field(
        title="Zero or more space-separated keywords relevant to this message."
    )
    urls: typing.List[str] = pydantic.Field(
        title="Zero or more space-separated URLS to JIRA tickets, screen shots, etc."
    )
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
    date_invalidated: typing.Optional[datetime.datetime] = pydantic.Field(
        description="TAI date at which is_valid was last set true."
    )
    parent_id: typing.Optional[uuid.UUID] = pydantic.Field(
        description="Message ID of message this is an edited version of."
    )

    class Config:
        orm_mode = True


MESSAGE_FIELDS = tuple(Message.schema()["properties"].keys())
