"""Configuration definition."""

__all__ = ["add_message_field"]

import graphql

from exposurelog.resolvers.add_message import add_message
from exposurelog.schemas.message_type import ExposureFlagType, MessageType

add_message_field = graphql.GraphQLField(
    MessageType,
    args=dict(
        obs_id=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="Observation ID (a string).",
        ),
        instrument=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="Short name of instrument (e.g. HSC).",
        ),
        message_text=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="Message text contains...",
        ),
        user_id=graphql.GraphQLArgument(
            graphql.GraphQLString, description="User ID."
        ),
        user_agent=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="User agent (which app created the message).",
        ),
        is_human=graphql.GraphQLArgument(
            graphql.GraphQLBoolean,
            description="Was the message created by a human being?",
        ),
        is_new=graphql.GraphQLArgument(
            graphql.GraphQLBoolean,
            description="Is the exposure new (and perhaps not "
            " yet ingested)? If True then it need not appear "
            "in either butler registry, and if it does not, "
            "then obs_id is computed using the current date.",
        ),
        exposure_flag=graphql.GraphQLArgument(
            ExposureFlagType,
            description="Optional flag for troublesome exposures.",
            default_value="none",
        ),
    ),
    resolve=add_message,
    description="Add a new message.",
)
