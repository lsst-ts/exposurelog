"""Configuration definition."""

__all__ = ["edit_message_field"]

import graphql

from explog.resolvers.edit_message import edit_message
from explog.schemas.message_type import ExposureFlagType, MessageType

edit_message_field = graphql.GraphQLField(
    MessageType,
    args=dict(
        id=graphql.GraphQLArgument(
            graphql.GraphQLNonNull(graphql.GraphQLInt),
            description="ID of message to edit.",
        ),
        message_text=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="Message text",
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
        exposure_flag=graphql.GraphQLArgument(
            ExposureFlagType,
            description="Optional flag for troublesome exposures.",
        ),
    ),
    resolve=edit_message,
    description="Edit an existing message. "
    "Omitted values are unchanged. "
    "This actually adds a new message with "
    "parent_id = ID of the original message, "
    "and sets is_valid False in the original message.",
)
