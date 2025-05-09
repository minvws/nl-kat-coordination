from nibbles.ask_network_questions.ask_network_questions import nibble

from octopoes.models.ooi.network import Network
from octopoes.models.ooi.question import Question


def test_ask_network_questions():
    results = list(nibble(Network(name="test1")))

    assert len(results) == 3
    assert isinstance(results[0], Question)
