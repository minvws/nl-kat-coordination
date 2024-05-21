from reports.report_types.greetings_report.report import GreetingsReport

from octopoes.models.tree import ReferenceTree


# Greeting|Hellloooo😺😺!!!|internet|13.107.236.208
def test_greetings_report_data_filled(mock_octopoes_api_connector, valid_time, hostname, tree_data_no_findings):
    mock_octopoes_api_connector.tree = {
        hostname.reference: ReferenceTree.model_validate(tree_data_no_findings),
    }

    report = GreetingsReport(mock_octopoes_api_connector)
    data = report.generate_data(str(hostname.reference), valid_time)
    assert data
