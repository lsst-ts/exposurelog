"""Configuration definition."""

__all__ = ["ExposureFlagType", "MessageType"]

import graphql

ExposureFlagType = graphql.GraphQLEnumType(
    name="ExposureFlag",
    values=dict(
        none=graphql.GraphQLEnumValue("none", description="No flag."),
        junk=graphql.GraphQLEnumValue(
            "junk", description="Exposure is hopelessly bad."
        ),
        questionable=graphql.GraphQLEnumValue(
            "questionable",
            description="Exposure is questionable; please examine it.",
        ),
    ),
    description="Flag this exposure as problematic",
)

MessageType = graphql.GraphQLObjectType(
    name="Message",
    fields=dict(
        id=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLInt),
            description="Message ID.",
        ),
        site_id=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLString),
            description="Site ID.",
        ),
        obs_id=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLString),
            description="Observation ID (a string).",
        ),
        instrument=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLString),
            description="Short name of instrument (e.g. HSC).",
        ),
        day_obs=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLInt),
            description="Day of observation; an integer with digits YYYYMMDD.",
        ),
        message_text=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLString),
            description="Message text.",
        ),
        user_id=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLString),
            description="User ID.",
        ),
        user_agent=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLString),
            description="User agent (which app created the message).",
        ),
        is_human=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLBoolean),
            description="Was the message created by a human being? "
            "(true=yes, false=no)",
        ),
        is_valid=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLBoolean),
            description="Is the message valid? "
            "(false if deleted or superseded).",
        ),
        exposure_flag=graphql.GraphQLField(
            graphql.GraphQLNonNull(ExposureFlagType),
            description="Optional flag for troublesome exposures.",
        ),
        date_added=graphql.GraphQLField(
            graphql.GraphQLNonNull(graphql.GraphQLString),
            description="Date the exposure was added; "
            "TAI as an ISO string.",
        ),
        date_is_valid_changed=graphql.GraphQLField(
            graphql.GraphQLString,
            description="Date the is_valid flag was last toggled; "
            "TAI as an ISO string; None if never toggled.",
        ),
        parent_id=graphql.GraphQLField(
            graphql.GraphQLInt,
            description="ID of parent message; None if no parent.",
        ),
        parent_site_id=graphql.GraphQLField(
            graphql.GraphQLString,
            description="Site ID.",
        ),
    ),
)
