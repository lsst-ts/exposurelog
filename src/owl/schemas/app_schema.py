"""Configuration definition."""

__all__ = ["app_schema"]

import graphql

from owl.schemas.add_message_field import add_message_field
from owl.schemas.delete_messages_field import delete_messages_field
from owl.schemas.edit_message_field import edit_message_field
from owl.schemas.find_messages_field import find_messages_field

app_schema = graphql.GraphQLSchema(
    query=graphql.GraphQLObjectType(
        name="Query",
        fields=dict(find_messages=find_messages_field),
    ),
    mutation=graphql.GraphQLObjectType(
        name="Mutation",
        fields=dict(
            add_message=add_message_field,
            delete_messages=delete_messages_field,
            edit_message=edit_message_field,
        ),
    ),
)
