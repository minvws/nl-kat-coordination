from typing import Dict, List

from factory import Factory, Sequence
from scheduler.models import BoefjeMeta, RawData


class RawDataFactory(Factory):
    class Meta:
        model = RawData

    id: str = Sequence(lambda n: n)
    boefje_meta: BoefjeMeta = None
    mime_types: List[Dict[str, str]] = [{"value": "text/plain"}, {"value": "text/html"}, {"value": "text/xml"}]
    secure_hash: str = ""
    hash_retrieval_link: str = ""
