"""
Keiko Web API
"""
import logging
import uuid
from pathlib import Path
from typing import List

from fastapi import FastAPI, BackgroundTasks, Body
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from keiko.base_models import ReportArgumentsBase
from keiko.health import get_health, ServiceHealth
from keiko.keiko import generate_report
from keiko.settings import Settings
from keiko.templates import get_templates, get_samples

settings = Settings()
logger = logging.getLogger(__name__)


def construct_api() -> FastAPI:
    """Constructs the FastAPI object, with prefilled examples from disk"""

    app = FastAPI()
    examples = get_samples()

    @app.get("/templates")
    def get_templates_() -> List[str]:
        """Endpoint to list known templates"""
        return list(get_templates())

    class ReportResponse(BaseModel):
        """Response model for the create report endpoint"""

        report_id: str

    @app.post("/reports")
    def create_report(
        parameters: ReportArgumentsBase = Body(..., examples=examples),
        background_tasks: BackgroundTasks = BackgroundTasks(),
    ) -> ReportResponse:
        """Endpoint to generate a report from a template"""

        # generate id
        report_id = str(uuid.uuid4())[:8]

        # generate template in background
        background_tasks.add_task(
            generate_report,
            template_name=parameters.template,
            report_data=parameters.data,
            glossary=parameters.glossary,
            report_id=report_id,
            debug=parameters.debug,
        )

        # return id
        return ReportResponse(report_id=report_id)

    @app.get("/health")
    def health() -> ServiceHealth:
        """Health endpoint"""
        return get_health()

    # mount reports as static files
    if not Path(settings.reports_folder).exists():
        Path(settings.reports_folder).mkdir(parents=True)
    app.mount("/reports", StaticFiles(directory=settings.reports_folder), name="reports")

    return app
