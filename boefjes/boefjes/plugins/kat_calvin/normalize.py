import json
from collections.abc import Iterator

from boefjes.job_models import NormalizerMeta
from octopoes.models.ooi.monitoring import Application, Incident


def run(normalizer_meta: NormalizerMeta, raw: str | bytes) -> Iterator[dict]:
    data = json.loads(raw)

    for log in data:
        yield from parse_log(log)


def parse_log(log: dict) -> Incident:
    app = Application(name=log.pop("client_environment_app"))

    yield {"type": "declaration", "ooi": app.dict()}

    mandatory_fields = {
        "event_id": str(log.pop("eventId")),
        "severity": log.pop("severity"),
        "event_title": log.pop("eventTitle"),
        "event_type": log.pop("eventType"),
    }

    yield {
        "type": "declaration",
        "ooi": Incident(
            application=app.reference,
            **mandatory_fields,
            meta_data=log,
        ).dict(),
    }
