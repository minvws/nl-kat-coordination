"""Server that exposes API endpoints for Octopoes."""

import logging
from pathlib import Path
from string import Template
from typing import Any, Dict, Optional, List

import uvicorn
from fastapi import FastAPI, status, Body, APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse
from graphql import print_schema, graphql_sync
from pydantic import BaseModel, Field
from requests import HTTPError

from octopoes.context.context import AppContext
from octopoes.ingesters.ingester import Ingester
from octopoes.models.health import ServiceHealth
from octopoes.models.ingester import Ingester as IngesterModel
from octopoes.version import version


class GraphqlRequest(BaseModel):
    """Request body for graphql queries."""

    operation_name: Optional[str] = Field(None, alias="operationName")
    query: str


class Server:
    """Server that exposes API endpoints for Octopoes."""

    def __init__(
        self,
        ctx: AppContext,
        ingesters: Dict[str, Ingester],
    ):
        """Initialize the server."""
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: AppContext = ctx
        self.ingesters = ingesters

        self.api = FastAPI()
        router = APIRouter(prefix="/{ingester_id}", dependencies=[Depends(self.extract_ingester)])

        self.api.add_api_route(
            path="/",
            endpoint=self.root,
            methods=["GET"],
            status_code=200,
        )

        self.api.add_api_route(
            path="/health",
            endpoint=self.health,
            methods=["GET"],
            response_model=ServiceHealth,
            status_code=200,
        )

        self.api.add_api_route(
            path="/ingesters",
            endpoint=self.get_ingesters,
            methods=["GET"],
            response_model=List[IngesterModel],
            status_code=200,
        )

        router.add_api_route(
            path="/graphiql",
            endpoint=self.get_graphiql,
            methods=["GET"],
            response_class=HTMLResponse,
            status_code=200,
        )

        router.add_api_route(
            path="/graphql-schema",
            endpoint=self.post_graphql,
            methods=["POST"],
            response_class=JSONResponse,
            status_code=200,
        )

        router.add_api_route(
            path="/graphql-schema",
            endpoint=self.get_graphql_schema,
            methods=["GET"],
            response_class=PlainTextResponse,
            status_code=200,
        )

        router.add_api_route(
            path="/ooi-schema",
            endpoint=self.get_ooi_schema,
            methods=["GET"],
            response_class=PlainTextResponse,
            status_code=200,
        )

        router.add_api_route(
            path="/objects/{object_id}",
            endpoint=self.get_object,
            methods=["GET"],
            response_class=JSONResponse,
            status_code=200,
        )

        router.add_api_route(
            path="/objects",
            endpoint=self.post_object,
            methods=["POST"],
            response_class=JSONResponse,
            status_code=200,
            openapi_extra={
                "requestBody": {
                    "examples": {
                        "test": '{"name": "test", "description": "test"}',
                    }
                }
            },
        )

        self.api.include_router(router)

    def extract_ingester(self, ingester_id: str) -> None:
        """Extract ingester from path parameter."""
        if ingester_id not in self.ingesters:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingester not found")

    def root(self) -> Any:
        """Root endpoint."""
        return None

    def health(self) -> Any:
        """Health endpoint."""
        response = ServiceHealth(
            service="octopoes",
            healthy=True,
            version=version,
        )

        for service in self.ctx.services.__dict__.values():
            response.externals[service.name] = service.is_healthy()

        for ingester_id, ingester in self.ingesters.items():
            try:
                ingester.xtdb_client.status()
                response.externals[ingester_id] = True
            except HTTPError:
                response.externals[ingester_id] = False

        response.healthy = all(response.externals.values())

        return response

    def get_ingesters(self) -> Any:
        """List ingesters."""
        return [IngesterModel(id=ingester) for ingester in self.ingesters]

    def get_graphql_schema(self, ingester_id: str) -> Any:
        """Serve graphql schema."""
        return print_schema(self.ingesters[ingester_id].current_schema.api_schema.schema)

    def get_ooi_schema(self, ingester_id: str) -> Any:
        """Serve graphql ooi schema (no backlinks)."""
        return print_schema(self.ingesters[ingester_id].current_schema.ooi_schema.schema)

    def get_object(self, ingester_id: str, object_id: str) -> Any:
        """Get an object."""
        return self.ingesters[ingester_id].object_repository.get(object_id)

    def get_graphiql(self, ingester_id: str) -> Any:
        """Serve graphiql frontend."""
        # load template from disk
        graphiql_template = Path(__file__).parent / "static" / "graphiql.html"
        with open(graphiql_template, "r") as graphiql_html:
            template = graphiql_html.read()
            return Template(template).substitute(ingester_id=ingester_id)

    def post_graphql(self, ingester_id: str, request_body: GraphqlRequest) -> Any:
        """Execute grqpql query."""
        result = graphql_sync(self.ingesters[ingester_id].current_schema.api_schema.schema, request_body.query)
        return result.formatted

    def post_object(
        self,
        ingester_id: str,
        object_data: Dict[str, Any] = Body(
            examples={
                "Network": {
                    "summary": "Network",
                    "description": "Create a network object.",
                    "value": {
                        "object_type": "Network",
                        "name": "TestNetwork",
                    },
                }
            },
        ),
    ) -> Any:
        """Post an object."""
        ingester = self.ingesters[ingester_id]
        obj = ingester.dataclass_generator.parse_obj(object_data)
        ingester.object_repository.save(obj)

        return 200

    def run(self) -> None:
        """Run the server."""
        uvicorn.run(
            self.api,
            host=self.ctx.config.api_host,
            port=self.ctx.config.api_port,
            log_config=None,
        )
