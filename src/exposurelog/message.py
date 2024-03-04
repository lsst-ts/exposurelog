__all__ = [
    "ExposureFlag",
    "Message",
    "MESSAGE_FIELDS",
    "MESSAGE_ORDER_BY_VALUES",
]

import datetime
import enum
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
    day_obs: int = pydantic.Field(
        description="Observation day, as an integer in the form YYYYMMDD."
    )
    seq_num: int = pydantic.Field(
        description="Counter for the observation within a larger sequence."
    )
    message_text: str = pydantic.Field(description="Message.")
    level: int = pydantic.Field(
        title="Message level. A python logging level: "
        "info=20, warning=30, error=40."
    )
    tags: list[str] = pydantic.Field(
        title="Zero or more space-separated keywords relevant to this message."
    )
    urls: list[str] = pydantic.Field(
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
    date_invalidated: None | datetime.datetime = pydantic.Field(
        description="TAI date at which is_valid was last set true."
    )
    parent_id: None | uuid.UUID = pydantic.Field(
        description="Message ID of message this is an edited version of."
    )

    model_config = {
        # Allow model_validate to work against SqlAlchemy database rows
        "from_attributes": True
    }


MESSAGE_FIELDS = tuple(Message.schema()["properties"].keys())


def _make_message_order_by_values() -> tuple[str, ...]:
    """Make a tuple of valid order_by values for find_messages.

    Return a tuple of all field names,
    plus those same field names with a leading "-".
    """
    order_by_values = []
    for field in Message.schema()["properties"]:
        order_by_values += [field, "-" + field]
    return tuple(order_by_values)


# Tuple of valid order_by fields.
# Each of these exists in the Message class.
MESSAGE_ORDER_BY_VALUES = _make_message_order_by_values()
