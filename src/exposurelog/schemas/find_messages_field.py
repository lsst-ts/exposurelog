"""Configuration definition."""

__all__ = ["find_messages_field"]

import graphql

from exposurelog.resolvers.find_messages import find_messages
from exposurelog.schemas.message_type import ExposureFlagType, MessageType

find_messages_field = graphql.GraphQLField(
    graphql.GraphQLList(MessageType),
    args=dict(
        min_id=graphql.GraphQLArgument(
            graphql.GraphQLInt,
            description="Minimum message ID, inclusive.",
        ),
        max_id=graphql.GraphQLArgument(
            graphql.GraphQLInt,
            description="Maximum message ID, exclusive.",
        ),
        obs_id=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="Observation ID (a string) contains...",
        ),
        instruments=graphql.GraphQLArgument(
            graphql.GraphQLList(graphql.GraphQLString),
            description="Names of instruments (e.g. HSC).",
        ),
        min_day_obs=graphql.GraphQLArgument(
            graphql.GraphQLInt,
            description="Minimum day of observation, inclusive; "
            "an integer of the form YYYYMMDD.",
        ),
        max_day_obs=graphql.GraphQLArgument(
            graphql.GraphQLInt,
            description="Maximum day of observation, exclusive; "
            "an integer of the form YYYYMMDD.",
        ),
        message_text=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="Message text contains...",
        ),
        user_ids=graphql.GraphQLArgument(
            graphql.GraphQLList(graphql.GraphQLString),
            description="User IDs.",
        ),
        user_agents=graphql.GraphQLArgument(
            graphql.GraphQLList(graphql.GraphQLString),
            description="User agent (which app created the message).",
        ),
        is_human=graphql.GraphQLArgument(
            graphql.GraphQLBoolean,
            description="Was the message created by a human being?",
        ),
        is_valid=graphql.GraphQLArgument(
            graphql.GraphQLBoolean,
            description="Is the message valid "
            "(False if deleted or superseded)?",
            default_value=True,
        ),
        exposure_flags=graphql.GraphQLArgument(
            graphql.GraphQLList(ExposureFlagType),
            description="List of exposure flag values",
        ),
        min_date_added=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="Minimum date the exposure was added, "
            "inclusive; TAI as an ISO string.",
        ),
        max_date_added=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="Maximum date the exposure was added, "
            "exclusive; TAI as an ISO string.",
        ),
        has_date_is_valid_changed=graphql.GraphQLArgument(
            graphql.GraphQLBoolean,
            description="Does this message have a non-null "
            "date_is_valid_changed?",
        ),
        min_date_is_valid_changed=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="Minimum date the is_valid flag "
            "was last toggled, inclusive; TAI as an ISO string.",
        ),
        max_date_is_valid_changed=graphql.GraphQLArgument(
            graphql.GraphQLString,
            description="Maximum date the is_valid flag "
            "was last toggled, exclusive; TAI as an ISO string.",
        ),
        has_parent_id=graphql.GraphQLArgument(
            graphql.GraphQLBoolean,
            description="Does this message have a " "non-null parent ID?",
        ),
        min_parent_id=graphql.GraphQLArgument(
            graphql.GraphQLInt,
            description="Minimum ID of parent message, inclusive.",
        ),
        max_parent_id=graphql.GraphQLArgument(
            graphql.GraphQLInt,
            description="Maximum ID of parent message, exclusive.",
        ),
        order_by=graphql.GraphQLArgument(
            graphql.GraphQLList(graphql.GraphQLString),
            description="Fields to sort by. "
            "Prefix a name with - for descending order, e.g. -id.",
        ),
    ),
    resolve=find_messages,
    description="Find messages. Note: consider specifying "
    "is_value=True as part of your query.",
)
