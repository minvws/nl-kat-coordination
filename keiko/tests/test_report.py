import pytest

from keiko.keiko import generate_report

import keiko.keiko

from templates.bevindingenrapport.model import DataShape

report_data_empty = {
    "meta": {
        "total": 0,
        "total_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "recommendation": 0},
        "total_by_finding_type": {},
        "total_finding_types": 0,
        "total_by_severity_per_finding_type": {"critical": 0, "high": 0, "medium": 0, "low": 0, "recommendation": 0},
    },
    "findings_grouped": {},
    "valid_time": "2022-08-26 08:23:58.373810+00:00",
    "ooi": {
        "id": "DNSZone|internet|mispo.es.",
        "ooi_type": "Hostname",
        "human_readable": "mispo.es.",
        "object_type": "Hostname",
    },
    "report_source_type": "Hostname",
    "report_source_value": "mispo.es.",
}


report_data_underscores = {
    "meta": {
        "total": 1,
        "total_by_severity": {"critical": 0, "high": 1, "medium": 0, "low": 0, "recommendation": 0},
        "total_by_finding_type": {},
        "total_finding_types": 1,
        "total_by_severity_per_finding_type": {"critical": 0, "high": 1, "medium": 0, "low": 0, "recommendation": 0},
    },
    "findings_grouped": {
        "KAT-OPEN-DATABASE-PORT": {
            "finding_type": {
                "id": "KAT-OPEN-DATABASE-PORT",
                "ooi_type": "KATFindingType",
                "human_readable": "KAT-OPEN-DATABASE-PORT",
                "object_type": "KATFindingType",
                "risk": "High",
                "description": "This description has __underscores__ in it",
                "recommendation": "Secure this port",
                "risk_level_source": "High",
                "risk_level_score": 8.9,
                "risk_level_severity": "high",
                "Information": "KAT findings",
                "findings": [],
            },
            "list": [
                {
                    "id": "Finding|IPPort|internet|134.209.85.72|tcp|3306|KAT-OPEN-DATABASE-PORT",
                    "ooi_type": "Finding",
                    "human_readable": "KAT-OPEN-DATABASE-PORT @ 134.209.85.72:3306/tcp",
                    "object_type": "Finding",
                    "proof": None,
                    "description": "This description has __underscores__ in it",
                    "reproduce": None,
                    "ooi": {
                        "id": "IPPort|internet|134.209.85.72|tcp|3306",
                        "ooi_type": "IPPort",
                        "human_readable": "134.209.85.72:3306/tcp",
                        "object_type": "IPPort",
                        "protocol": "tcp",
                        "port": "3306",
                        "state": "open",
                    },
                    "finding_type": {
                        "id": "KAT-OPEN-DATABASE-PORT",
                        "ooi_type": "KATFindingType",
                        "human_readable": "KAT-OPEN-DATABASE-PORT",
                        "object_type": "KATFindingType",
                        "risk": "High",
                        "description": "A database port is open.",
                        "recommendation": "Secure this port",
                        "risk_level_source": "High",
                        "risk_level_score": 8.9,
                        "risk_level_severity": "high",
                        "Information": "KAT findings",
                        "findings": [],
                    },
                }
            ],
        },
    },
    "valid_time": "2022-08-26 08:23:58.373810+00:00",
    "ooi": {
        "id": "DNSZone|internet|mispo.es.",
        "ooi_type": "Hostname",
        "human_readable": "mispo.es.",
        "object_type": "Hostname",
    },
    "report_source_type": "Hostname",
    "report_source_value": "mispo.es.",
}


@pytest.fixture
def report_args():
    return {
        "template_name": "bevindingenrapport",
        "glossary": "dutch.hiero.csv",
        "debug": False,
        "report_id": "test",
    }


def test_generate_report_empty(report_args, tmp_path):
    keiko.keiko.settings.reports_folder = str(tmp_path)

    report_args["report_data"] = DataShape.parse_obj(report_data_empty)
    generate_report(**report_args)

    report_file = tmp_path / "test.keiko.pdf"
    tex_file = tmp_path / "test.keiko.tex"
    json_file = tmp_path / "test.keiko.json"
    assert report_file.exists()
    assert not tex_file.exists()
    assert not json_file.exists()


def test_generate_report_debug(report_args, tmp_path):
    keiko.keiko.settings.reports_folder = tmp_path

    report_args["report_data"] = DataShape.parse_obj(report_data_empty)
    report_args["debug"] = True
    generate_report(**report_args)

    report_file = tmp_path / "test.keiko.pdf"
    tex_file = tmp_path / "test.keiko.tex"

    assert report_file.exists()
    assert tex_file.exists()


def test_generate_report_underscore(report_args, tmp_path):
    keiko.keiko.settings.reports_folder = tmp_path

    report_args["report_data"] = DataShape.parse_obj(report_data_underscores)
    generate_report(**report_args)

    report_file = tmp_path / "test.keiko.pdf"
    assert report_file.exists()
