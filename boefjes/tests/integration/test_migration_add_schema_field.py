import os
from unittest import TestCase, skipIf

import alembic.config
from psycopg2.extras import execute_values
from sqlalchemy.orm import sessionmaker

from boefjes.local_repository import get_local_repository
from boefjes.sql.db import SQL_BASE, get_engine


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestSettingsToBoefjeConfig(TestCase):
    def setUp(self) -> None:
        self.engine = get_engine()

        # To reset autoincrement ids
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "downgrade", "base"])
        # Set state to revision 6f99834a4a5a
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "f9de6eb7824b"])

        dns_records = get_local_repository().by_id("dns-records")
        nmap_udp = get_local_repository().by_id("nmap-udp")

        entries = [
            (
                boefje.id,
                boefje.name,
                boefje.description,
                str(boefje.scan_level),
                list(sorted(boefje.consumes)),
                list(sorted(boefje.produces)),
                boefje.environment_keys,
                boefje.oci_image,
                boefje.oci_arguments,
                boefje.version,
            )
            for boefje in [dns_records, nmap_udp]
        ]

        connection = self.engine.connect()
        query = """INSERT INTO boefje (plugin_id, name, description, scan_level, consumes, produces, environment_keys,
                oci_image, oci_arguments, version) values %s"""

        with connection.begin():
            execute_values(connection.connection.cursor(), query, entries)

    def test_fail_on_wrong_plugin_ids(self):
        assert self.engine.execute("SELECT * from boefje").fetchall() == [
            (
                1,
                "dns-records",
                None,
                "DNS records",
                "Fetch the DNS record(s) of a hostname",
                "1",
                ["Hostname"],
                ["boefje/dns-records"],
                ["RECORD_TYPES", "REMOTE_NS"],
                None,
                [],
                None,
                False,
            ),
            (
                2,
                "nmap-udp",
                None,
                "Nmap UDP",
                "Defaults to top 250 UDP ports. Includes service detection.",
                "2",
                ["IPAddressV4", "IPAddressV6"],
                ["boefje/nmap-udp"],
                ["TOP_PORTS_UDP"],
                "ghcr.io/minvws/openkat/nmap:latest",
                ["--open", "-T4", "-Pn", "-r", "-v10", "-sV", "-sU"],
                None,
                False,
            ),
        ]

        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "5be152459a7b"])

        schema_dns = {
            "title": "Arguments",
            "type": "object",
            "properties": {
                "RECORD_TYPES": {
                    "title": "RECORD_TYPES",
                    "type": "string",
                    "description": "List of comma separated DNS record types to query for.",
                    "default": "A,AAAA,CAA,CERT,RP,SRV,TXT,MX,NS,CNAME,DNAME",
                },
                "REMOTE_NS": {
                    "title": "REMOTE_NS",
                    "maxLength": 45,
                    "type": "string",
                    "description": "The IP address of the DNS resolver you want to use.",
                    "default": "1.1.1.1",
                },
            },
        }

        schema_udp = {
            "title": "Arguments",
            "type": "object",
            "properties": {
                "TOP_PORTS_UDP": {
                    "title": "TOP_PORTS_UDP",
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 65535,
                    "description": "Scan TOP_PORTS_UDP most common ports. Defaults to 250.",
                }
            },
            "required": [],
        }

        self.assertListEqual(
            self.engine.execute("SELECT * from boefje").fetchall(),
            [
                (
                    1,
                    "dns-records",
                    None,
                    "DNS records",
                    "Fetch the DNS record(s) of a hostname",
                    "1",
                    ["Hostname"],
                    ["boefje/dns-records"],
                    ["RECORD_TYPES", "REMOTE_NS"],
                    None,
                    [],
                    None,
                    False,
                    schema_dns,
                ),
                (
                    2,
                    "nmap-udp",
                    None,
                    "Nmap UDP",
                    "Defaults to top 250 UDP ports. Includes service detection.",
                    "2",
                    ["IPAddressV4", "IPAddressV6"],
                    ["boefje/nmap-udp"],
                    ["TOP_PORTS_UDP"],
                    "ghcr.io/minvws/openkat/nmap:latest",
                    ["--open", "-T4", "-Pn", "-r", "-v10", "-sV", "-sU"],
                    None,
                    False,
                    schema_udp,
                ),
            ],
        )

    def tearDown(self) -> None:
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"])

        session = sessionmaker(bind=get_engine())()

        for table in SQL_BASE.metadata.tables:
            session.execute(f"DELETE FROM {table} CASCADE")  # noqa: S608

        session.commit()
        session.close()
