"""Configuration definition."""

__all__ = ["delete_messages_field"]

import graphql

from explog.resolvers.delete_messages import delete_messages
from explog.schemas.message_type import MessageType

delete_messages_field = graphql.GraphQLField(
    graphql.GraphQLList(MessageType),
    args=dict(
        ids=graphql.GraphQLArgument(
            graphql.GraphQLList(graphql.GraphQLInt),
            description="Message IDs.",
        ),
    ),
    resolve=delete_messages,
    description="Delete one or more messages. "
    "Do this by setting is_valid False "
    "and updating date_is_valid_changed",
)
