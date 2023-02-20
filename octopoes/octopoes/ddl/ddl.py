"""KAT GraphQL DDL module."""
from __future__ import annotations

import re
from functools import cached_property
from logging import getLogger
from pathlib import Path
from typing import Optional

from graphql import (
    build_schema,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLUnionType,
    GraphQLField,
    GraphQLList,
    GraphQLString,
    extend_schema,
    parse,
    GraphQLArgument,
    DocumentNode,
    DirectiveDefinitionNode,
    ObjectTypeDefinitionNode,
    TypeDefinitionNode,
    ScalarTypeDefinitionNode,
    InputObjectTypeDefinitionNode,
    UnionTypeDefinitionNode,
    EnumTypeDefinitionNode,
    InterfaceTypeDefinitionNode,
)

from octopoes.ddl.schema import BaseSchema, CompleteSchema, APISchema

logger = getLogger(__name__)


class SchemaValidationException(Exception):
    """Exception raised when a schema is invalid."""


# Types that are already used by the GraphQL library and should not be used in KAT schemas
BUILTIN_TYPES = {
    "String",
    "Int",
    "Float",
    "Boolean",
    "ID",
    "__Schema",
    "__Type",
    "__TypeKind",
    "__Field",
    "__InputValue",
    "__EnumValue",
    "__Directive",
    "__DirectiveLocation",
}

RESERVED_TYPE_NAMES = {
    "Query",
    "Mutation",
    "Subscription",
    "BaseObject",
    "OOI",
}

BASE_SCHEMA_FILE = Path(__file__).parent / "schemas" / "base_schema.graphql"
OOI_SCHEMA_FILE = Path(__file__).parent / "schemas" / "ooi_schema.graphql"
COMPLETE_SCHEMA_FILE = Path(__file__).parent / "schemas" / "complete_schema.graphql"


class SchemaLoader:
    """Load an OOI schema definition to validate and calculate derived schemas.

    Initialized with an OOI schema definition string.
    Derived schemas:
    - base_schema: The base schema, which the OOI schema extends
    - ooi_schema: The OOI schema, which is validated
    - complete_schema: The OOI schema, extended with KAT specific types
    - api_schema: The full schema, where reverse fields are linked. Extended with Query type.
      Meant to expose to API
    """

    def __init__(self, ooi_schema_definition: Optional[str] = None):
        """Initialize instance."""
        self.ooi_schema_definition = (
            ooi_schema_definition if ooi_schema_definition is not None else OOI_SCHEMA_FILE.read_text()
        )
        self.validate_ooi_schema()

    @cached_property
    def base_schema(self) -> BaseSchema:
        """Return and cache the base schema."""
        return BaseSchema(build_schema(BASE_SCHEMA_FILE.read_text()))

    @cached_property
    def ooi_schema_document(self) -> DocumentNode:
        """Return and cache the parsed OOI schema."""
        return parse(self.ooi_schema_definition)

    @cached_property
    def ooi_schema(self) -> BaseSchema:
        """Load the schema from disk."""
        return BaseSchema(extend_schema(self.base_schema.schema, self.ooi_schema_document))

    def validate_type_definition_node(self, node: TypeDefinitionNode) -> str:
        """Validate type definitions in general."""
        if node.name.value in RESERVED_TYPE_NAMES or node.name.value in BUILTIN_TYPES:
            return f"Use of reserved type name is not allowed [type={node.name.value}]"

        if not re.match(r"^[A-Z]+[a-z]*(?:\d*(?:[A-Z]+[a-z]*)?)*$", node.name.value):
            return f"Object types must follow PascalCase conventions [type={node.name.value}]"

        # Validate that natural keys are defined as fields
        if not isinstance(  # pylint: disable=too-many-nested-blocks
            node,
            (UnionTypeDefinitionNode, EnumTypeDefinitionNode, InterfaceTypeDefinitionNode, ScalarTypeDefinitionNode),
        ):
            natural_keys = set()
            fields = set()
            for field in node.fields:

                fields.add(field.name.value)
                if field.name.value == "primary_key":
                    for argument in field.arguments:
                        if argument.name.value == "natural_key":
                            for value in argument.default_value.values:
                                natural_keys.add(value.value)

            for natural_key in natural_keys:
                if natural_key not in fields:
                    return (
                        f"Natural keys must be defined as fields "
                        f"[type={node.name.value}, natural_key={natural_key}]"
                    )

            # Validate that the BaseObject and OOI interfaces are properly implemented
            if not {"primary_key", "object_type", "human_readable"}.issubset(fields):
                return (
                    f"The BaseObject and OOI interfaces must be implemented properly "
                    f"[type={node.name.value} primary_key^object_type^human_readable]"
                )

        return ""

    def validate_union_definition_node(self, node: UnionTypeDefinitionNode) -> str:
        """Validate that all union nodes start with a U."""
        if not node.name.value.startswith("U"):
            return f"Self-defined unions must start with a U [type={node.name.value}]"
        return ""

    def validate_object_type_definition_node(self, node: ObjectTypeDefinitionNode) -> str:
        """Validate that all types inherit from BaseObject and OOI."""
        interface_names = [interface.name.value for interface in node.interfaces]
        if "BaseObject" not in interface_names and "OOI" not in interface_names:
            return f"An object must inherit both BaseObject and OOI (missing both) [type={node.name.value}]"
        if "BaseObject" not in interface_names and "OOI" in interface_names:
            return f"An object must inherit both BaseObject and OOI (missing BaseObject) [type={node.name.value}]"
        if "BaseObject" in interface_names and "OOI" not in interface_names:
            return f"An object must inherit both BaseObject and OOI (missing OOI) [type={node.name.value}]"

        return ""

    def validate_directive_definition_node(self, node: DirectiveDefinitionNode) -> str:
        """Validate that directives are not defined in the schema."""
        return (
            f"A schema may only define a Type, Enum, Union, or Interface, not Directive "
            f"[directive={node.name.value}]"
        )

    def validate_input_object_definition_node(self, node: InputObjectTypeDefinitionNode) -> str:
        """Validate that inputs are not defined in the schema."""
        return f"A schema may only define a Type, Enum, Union, or Interface, not Input [type={node.name.value}]"

    def validate_scalar_type_definition_node(self, node: ScalarTypeDefinitionNode) -> str:
        """Validate that scalars are not defined in the schema."""
        return f"A schema may only define a Type, Enum, Union, or Interface, not Scalar [type={node.name.value}]"

    def validate_ooi_schema(self) -> None:
        """Look into the AST of the schema definition file to apply restrictions.

        References:
            - https://graphql-core-3.readthedocs.io/en/latest/modules/language.html
        """
        validators = [
            (lambda x: issubclass(type(x), UnionTypeDefinitionNode), self.validate_union_definition_node),
            (lambda x: issubclass(type(x), ObjectTypeDefinitionNode), self.validate_object_type_definition_node),
            (lambda x: issubclass(type(x), DirectiveDefinitionNode), self.validate_directive_definition_node),
            (
                lambda x: issubclass(type(x), InputObjectTypeDefinitionNode),
                self.validate_input_object_definition_node,
            ),
            (lambda x: issubclass(type(x), TypeDefinitionNode), self.validate_type_definition_node),
            (lambda x: issubclass(type(x), ScalarTypeDefinitionNode), self.validate_scalar_type_definition_node),
        ]

        for definition in self.ooi_schema_document.definitions:
            for validator in validators:
                if validator[0](definition):  # type: ignore
                    if error_message := validator[1](definition):
                        raise SchemaValidationException(error_message)

    @cached_property
    def complete_schema_document(self) -> DocumentNode:
        """Return and cache the base schema."""
        return parse(COMPLETE_SCHEMA_FILE.read_text())

    @cached_property
    def complete_schema(self) -> CompleteSchema:
        """Build the complete schema by adding Octopoes default concrete, like Origin and ScanProfile.

        Combine all concrete types into a single union type.
        Load the complete schema from file.
        """
        # Create a new GraphQLSchema including OOI Union = all object types that implement OOI
        ooi_union = GraphQLUnionType("UOOI", types=self.ooi_schema.object_types)

        complete_schema_kwargs = self.ooi_schema.schema.to_kwargs()
        complete_schema_kwargs["types"] += (ooi_union,)

        complete_schema = extend_schema(GraphQLSchema(**complete_schema_kwargs), self.complete_schema_document)

        return CompleteSchema(complete_schema)

    @cached_property
    def api_schema(self) -> APISchema:
        """Construct the hydrated schema by adding backlinks and Query/Mutation types."""
        # Create backlinks
        for type_ in self.complete_schema.object_types:
            for field_name, field in type_.fields.items():

                if getattr(field.type, "of_type", None) is None:
                    continue

                target_field_type = field.type.of_type

                if not isinstance(target_field_type, GraphQLObjectType):
                    continue

                if field.args.get("backlink", None):
                    continue

                target_field_type.fields[field.args["reverse_name"].default_value] = GraphQLField(
                    GraphQLList(type_), {"backlink": GraphQLArgument(GraphQLString, default_value=field_name)}
                )

        # Construct Query Type
        query_fields = {type_.name: GraphQLField(GraphQLList(type_)) for type_ in self.complete_schema.object_types}
        query_fields["OOI"] = GraphQLField(GraphQLList(self.complete_schema.ooi_union_type))
        query = GraphQLObjectType("Query", fields=query_fields)

        # Construct Mutation Type
        hydrated_schema_kwargs = self.complete_schema.schema.to_kwargs()
        hydrated_schema_kwargs["query"] = query
        hydrated_schema_kwargs["types"] = hydrated_schema_kwargs["types"] + (query,)

        return APISchema(GraphQLSchema(**hydrated_schema_kwargs))
