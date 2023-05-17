import json
from pathlib import Path
from typing import Iterator, List

from octopoes.models import OOI
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.question import Question


def run(
    input_ooi: Network,
    additional_oois: List,
) -> Iterator[OOI]:
    network = input_ooi

    with (Path(__file__).parent / "question_schema.json").open() as f:
        schema = json.load(f)

    yield Question(ooi=network.reference, schema_id=schema["$id"], json_schema=json.dumps(schema))
