import json
from pathlib import Path
from typing import Dict, Iterator, List

from octopoes.models import OOI
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.question import Question


def run(
    input_ooi: Network,
    additional_oois: List,
    config: Dict[str, str],
) -> Iterator[OOI]:
    network = input_ooi

    with open(Path(__file__).parent / "question_schema.json") as f:
        schema = json.load(f)

    yield Question(ooi=network.reference, schema_id=schema["$id"], json_schema=json.dumps(schema))
