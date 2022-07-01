from typing import List, Optional

from pydantic import BaseModel, Field

from .boefje import Boefje, BoefjeMeta
from .normalizer import Normalizer


class NormalizerTask(BaseModel):
    """NormalizerTask represent data needed for a Normalizer to run."""

    id: Optional[str]
    normalizer: Normalizer
    boefje_meta: BoefjeMeta

    def __hash__(self):
        """Make NormalizerTask hashable, so that we can de-duplicate it when
        used in the PriorityQueue. We hash the combination of the attributes
        normalizer.id since this combination is unique."""
        return hash((self.normalizer.id, self.boefje_meta.id))


class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run."""

    id: Optional[str]
    boefje: Boefje
    input_ooi: str
    organization: str

    dispatches: List[Normalizer] = Field(default_factory=list)

    def __hash__(self) -> int:
        """Make BoefjeTask hashable, so that we can de-duplicate it when used
        in the PriorityQueue. We hash the combination of the attributes
        input_ooi and boefje.id since this combination is unique."""
        return hash((self.input_ooi, self.boefje.id, self.organization))
