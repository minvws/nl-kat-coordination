from bits.ask_port_specification.ask_port_specification import run

from octopoes.models.ooi.network import Network
from octopoes.models.ooi.question import Question


def test_port_classification_tcp_80():
    results = list(run(Network(name="test1"), [], {}))

    assert len(results) == 1
    assert isinstance(results[0], Question)
