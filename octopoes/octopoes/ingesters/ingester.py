"""Main processing logic for Octopoes."""
import logging
import threading
from typing import Callable, Optional, Any, NoReturn

from graphql import GraphQLResolveInfo, GraphQLUnionType, GraphQLObjectType
from requests import HTTPError

from octopoes.connectors.services.xtdb import XTDBHTTPClient, XTDBSession, OperationType
from octopoes.context.context import AppContext
from octopoes.ddl.dataclasses import DataclassGenerator
from octopoes.ddl.ddl import SchemaLoader
from octopoes.models.organisation import Organisation
from octopoes.repositories.object_repository import ObjectRepository
from octopoes.utils.thread import ThreadRunner

logger = logging.getLogger(__name__)


class Ingester:  # pylint: disable=too-many-instance-attributes
    """Main data ingestion unit for an Organization."""

    def __init__(
        self,
        ctx: AppContext,
        ingester_id: str,
        organisation: Organisation,
    ):
        """Initialize the ingester."""
        self.organisation = organisation

        self.ctx = ctx
        self.ingester_id = ingester_id
        self.thread: Optional[ThreadRunner] = None
        self.stop_event: threading.Event = self.ctx.stop_event

        self.xtdb_client = XTDBHTTPClient(f"{self.ctx.config.xtdb_uri}/_dev")

        # Try to load the current_schema from XTDB
        self.current_schema = self.load_schema()
        self.dataclass_generator = DataclassGenerator(self.current_schema.complete_schema)
        self.setup_resolvers()
        self.object_repository = ObjectRepository(self.current_schema, self.dataclass_generator, self.xtdb_client)

    def update_schema(self, new_schema: SchemaLoader) -> None:
        """Update the current_schema and update XTDB as well as in-memory structures."""
        self.current_schema = new_schema
        self.persist_schema()
        self.dataclass_generator = DataclassGenerator(self.current_schema.complete_schema)
        self.setup_resolvers()
        self.object_repository = ObjectRepository(self.current_schema, self.dataclass_generator, self.xtdb_client)

    def load_schema(self) -> SchemaLoader:
        """Load the current_schema from XTDB."""
        try:
            current_schema_def = self.xtdb_client.get_entity("schema")
            current_schema = SchemaLoader(current_schema_def["schema"])
            current_schema = SchemaLoader()
        except HTTPError as exc:
            if exc.response.status_code == 404:
                logger.info("No current_schema found in XTDB, using OpenKAT schema from disk")
                current_schema = SchemaLoader()
            else:
                raise exc
        return current_schema

    def persist_schema(self) -> None:
        """Persist the schema to XTDB."""
        xtdb_session = XTDBSession(self.xtdb_client)
        document = {
            "xt/id": "schema",
            "schema": self.current_schema.ooi_schema_definition,
        }
        xtdb_session.add((OperationType.PUT, document, None))
        xtdb_session.commit()

    def run_in_thread(
        self,
        func: Callable[[], Any],
        interval: float = 0.01,
        daemon: bool = False,
    ) -> None:
        """Make a function run in a thread, and add it to the dict of threads."""
        self.thread = ThreadRunner(
            target=func,
            stop_event=self.stop_event,
            interval=interval,
            daemon=daemon,
        )
        self.thread.start()

    def stop(self) -> None:
        """Stop the ingesters."""
        if self.thread is not None:
            self.thread.join(5)

        logger.info("Stopped ingesters: %s", self.ingester_id)

    def run(self) -> NoReturn:  # type: ignore
        """Run the ingester."""
        self.run_in_thread(
            func=self.ingest,
            interval=30,
        )

    def resolve_graphql_union(self, data: Any, _: GraphQLResolveInfo, __: GraphQLUnionType) -> Any:
        """Resolve a GraphQL union type to an object type."""
        return data["object_type"]

    def resolve_graphql_type(
        self, parent_obj: Any, type_info: GraphQLResolveInfo, **kwargs: Any  # pylint: disable=unused-argument
    ) -> Any:
        """Fetch instances of type from XTDB."""
        # outgoing relation
        if parent_obj and type_info.field_name in parent_obj:
            return self.object_repository.get(parent_obj[type_info.field_name])

        # backlink
        if parent_obj:
            return self.object_repository.list_by_incoming_relation(
                parent_obj["primary_key"], type_info.return_type.of_type.name, kwargs["backlink"]
            )

        return self.object_repository.list_by_object_type(type_info.return_type.of_type.name)

    def setup_resolvers(self) -> None:
        """Set resolvers for GraphQL schema."""
        # Set resolver for root OOI union type
        self.current_schema.api_schema.schema.query_type.fields["OOI"].resolve = self.resolve_graphql_type

        # Setup type resolver for all union types
        for union_type in self.current_schema.api_schema.union_types:
            union_type.resolve_type = self.resolve_graphql_union

        # Setup resolvers for all fields
        for object_type in self.current_schema.api_schema.object_types:
            for field in object_type.fields.values():
                real_type = field.type.of_type if getattr(field.type, "of_type", None) else field.type
                if isinstance(real_type, GraphQLObjectType):
                    field.resolve = self.resolve_graphql_type
                if isinstance(real_type, GraphQLUnionType):
                    field.resolve = self.resolve_graphql_type

    def ingest(self) -> None:
        """Periodically ingest data."""
        logger.info("Ingesting... %s", self.ingester_id)

        # create node in XTDB
        XTDBHTTPClient(f"{self.ctx.config.xtdb_uri}").create_node(self.ingester_id)

        # load new current_schema
        new_schema = SchemaLoader()

        # compare with previous current_schema and validate
        if new_schema.ooi_schema_definition != self.current_schema.ooi_schema_definition:
            logger.info("New schema detected, updating")
            self.update_schema(new_schema)

        # ingest normalizer configs
        # ingest bit configs

        # ingest normalizer outputs / origins

        # wait for processing to complete

        # loop(while things to do)
        # execute relational bits
        # wait for processing to complete

        # perform dynamic programming computations
        # - propagate scan profiles

        # persist valid-time, transaction-time pair as consolidated
