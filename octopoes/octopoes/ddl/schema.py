"""This module defines the classes that represent the Octopoes GraphQL schema layers.

The Octopoes GraphQL schema is hierarchical, composed of the following layers:

BaseSchema: Fixed schema with the Octopoes base-interfaces and -scalars.
OOISchema: Extends BaseSchema with user-configured OOI types.
CompleteSchema: Extends OOISchema with KAT concrete types like Origin and ScanProfile.
APISchema: Extends CompleteSchema with backlink-properties and Query type. This layer is presented to the API.
"""
from typing import cast, List

from graphql import GraphQLSchema, GraphQLInterfaceType, GraphQLObjectType, GraphQLUnionType


class BaseSchema:
    """Contain the Octopoes base-schema and expose conveniant properties to access base-types.

    Loaded from base_schema.graphql.
    """

    def __init__(self, schema: GraphQLSchema) -> None:
        """Initialize instance."""
        self.schema = schema

    @property
    def base_object_type(self) -> GraphQLInterfaceType:
        """Return the BaseObject type."""
        return cast(GraphQLInterfaceType, self.schema.type_map["BaseObject"])

    @property
    def ooi_type(self) -> GraphQLInterfaceType:
        """Return the OOI type."""
        return cast(GraphQLInterfaceType, self.schema.type_map["OOI"])

    @property
    def object_types(self) -> List[GraphQLObjectType]:
        """Return all object types."""
        return [
            t
            for t in self.schema.type_map.values()
            if isinstance(t, GraphQLObjectType) and not t.name.startswith("__")
        ]

    @property
    def union_types(self) -> List[GraphQLUnionType]:
        """Return all union types."""
        return [
            t for t in self.schema.type_map.values() if isinstance(t, GraphQLUnionType) and not t.name.startswith("__")
        ]

    def get_object_type(self, name: str) -> GraphQLObjectType:
        """Return the object type with the given name."""
        return cast(GraphQLObjectType, self.schema.type_map[name])


class OOISchema(BaseSchema):
    """Contains the user-configured OOI schema.

    Loaded from ooi_schema.graphql.
    """


class CompleteSchema(BaseSchema):
    """Contains the complete schema and exposes convenient properties to access concrete types.

    Loaded from complete_schema.graphql.
    """

    @property
    def ooi_union_type(self) -> GraphQLUnionType:
        """Return the OOI union type."""
        return cast(GraphQLUnionType, self.schema.type_map["UOOI"])

    @property
    def origin_type(self) -> GraphQLObjectType:
        """Return the Origin type."""
        return cast(GraphQLObjectType, self.schema.type_map["Origin"])

    @property
    def scan_profile_type(self) -> GraphQLObjectType:
        """Return the ScanProfile type."""
        return cast(GraphQLObjectType, self.schema.type_map["ScanProfile"])


class APISchema(CompleteSchema):
    """Hydrate CompleteSchema with backlinks. Add Query type.

    This schema is exposed to the GraphQL API for querying.
    Generated in-memory
    """

    @property
    def query_type(self) -> GraphQLObjectType:
        """Return the Query type."""
        return cast(GraphQLObjectType, self.schema.type_map["Query"])
