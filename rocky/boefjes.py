import uuid
from typing import Dict, Optional, Any

from octopoes.models import Reference
from pydantic import BaseModel

from rocky.celery import app
from rocky.katalogus import Boefje
from tools.models import Organization, Job


class BoefjeTask(BaseModel):
    id: Optional[str]
    boefje: Boefje
    input_ooi: Reference
    organization: str
    arguments: Dict = {}

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.id = str(uuid.uuid4())


class IndemnificationNotPresent(Exception):
    """Exception suggesting there is no indemnification present"""


def run_boefje(boefje_task: BoefjeTask, organization: Organization) -> None:
    _create_job_from_boefje(boefje_task, organization)

    app.send_task(
        "tasks.handle_boefje",
        (to_task(boefje_task),),
        queue="boefjes",
        task_id=str(boefje_task.id),
    )


def _create_job_from_boefje(boefje_task: BoefjeTask, organization: Organization):
    return Job.objects.create(
        id=boefje_task.id,
        organization=organization,
        boefje_id=boefje_task.boefje.id,
        input_ooi=str(boefje_task.input_ooi),
        arguments=boefje_task.arguments,
    )


def to_task(boefje_task: BoefjeTask) -> Dict:
    return {
        "id": str(boefje_task.id),
        "input_ooi": str(boefje_task.input_ooi),
        "boefje": {
            "id": boefje_task.boefje.id,
            "version": None,
        },
        "organization": boefje_task.organization,
        "arguments": boefje_task.arguments,
    }
