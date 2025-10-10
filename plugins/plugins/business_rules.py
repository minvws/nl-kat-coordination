from collections.abc import Sequence

import structlog
from django.db.models import Case, Count, F, When
from djangoql.exceptions import DjangoQLParserError
from djangoql.queryset import apply_search
from djangoql.schema import DjangoQLSchema, IntField

from objects.models import DNSTXTRecord, Finding, FindingType, Hostname, bulk_insert
from plugins.models import BusinessRule

logger = structlog.get_logger(__name__)


SA_TCP_PORTS = [21, 22, 23, 5900]
DB_TCP_PORTS = [1433, 1434, 3050, 3306, 5432]
MICROSOFT_RDP_PORTS = [3389]
COMMON_TCP_PORTS = [25, 53, 80, 110, 143, 443, 465, 587, 993, 995]
ALL_COMMON_TCP = COMMON_TCP_PORTS + SA_TCP_PORTS + DB_TCP_PORTS + MICROSOFT_RDP_PORTS
COMMON_UDP_PORTS = [53]
INDICATORS = [
    "ns1.registrant-verification.ispapi.net",
    "ns2.registrant-verification.ispapi.net",
    "ns3.registrant-verification.ispapi.net",
]


def get_rules():
    BUSINESS_RULES = {
        "ipv6_webservers": {
            "name": "ipv6_webservers",
            "description": "Checks if webserver has IPv6 support",
            "object_type": "hostname",
            "query": "dnsnsrecord_nameserver = None and dnsaaaarecord = None",
            "finding_type_code": "KAT-WEBSERVER-NO-IPV6",
        },
        "ipv6_nameservers": {
            "name": "ipv6_nameservers",
            "description": "Checks if nameserver has IPv6 support",
            "object_type": "hostname",
            "query": "dnsnsrecord_nameserver != None and dnsaaaarecord = None",
            "finding_type_code": "KAT-NAMESERVER-NO-IPV6",
        },
        "two_ipv6_nameservers": {
            "name": "two_ipv6_nameservers",
            "description": "Checks if a hostname has at least two nameservers supporting IPv6",
            "object_type": "hostname",
            "query": "dnsnsrecord_nameserver = None and nameservers_with_ipv6_count < 2",
            "finding_type_code": "KAT-NAMESERVER-NO-TWO-IPV6",
        },
        "missing_spf": {
            "name": "missing_spf",
            "description": "Checks is the hostname has valid SPF records",
            "object_type": "hostname",
            "query": f"""
                SELECT "{Hostname._meta.db_table}".*
                FROM "{Hostname._meta.db_table}"
                LEFT JOIN "{DNSTXTRecord._meta.db_table}"
                   ON (
                   "{Hostname._meta.db_table}"."_id" = "{DNSTXTRecord._meta.db_table}"."hostname_id"
                   AND "{DNSTXTRecord._meta.db_table}"."value"::text LIKE 'v=spf1%%'
                )
                WHERE "{DNSTXTRecord._meta.db_table}"._id IS NULL;
            """,  # noqa: S608
            "finding_type_code": "KAT-NO-SPF",
        },
        "open_sysadmin_port": {
            "name": "open_sysadmin_port",
            "description": "Detect open sysadmin ports",
            "object_type": "ipport",
            "query": f'protocol = "TCP" and port in ({", ".join(str(x) for x in SA_TCP_PORTS)})',
            "finding_type_code": "KAT-OPEN-SYSADMIN-PORT",
        },
        "open_database_port": {
            "name": "open_database_port",
            "description": "Detect open database ports",
            "object_type": "ipport",
            "query": f'protocol = "TCP" and port in ({", ".join(str(x) for x in DB_TCP_PORTS)})',
            "finding_type_code": "KAT-OPEN-DATABASE-PORT",
        },
        "open_remote_desktop_port": {
            "name": "open_remote_desktop_port",
            "description": "Detect open RDP ports",
            "object_type": "ipport",
            "query": f'protocol = "TCP" and port in ({", ".join(str(x) for x in MICROSOFT_RDP_PORTS)})',
            "finding_type_code": "KAT-REMOTE-DESKTOP-PORT",
        },
        "open_uncommon_port": {
            "name": "open_uncommon_port",
            "description": "Detect open uncommon ports",
            "object_type": "ipport",
            "query": f'(protocol = "TCP" and port not in ({", ".join(str(x) for x in ALL_COMMON_TCP)})) '
            f'or (protocol = "UDP" and port not in ({", ".join(str(x) for x in COMMON_UDP_PORTS)}))',
            "finding_type_code": "KAT-UNCOMMON-OPEN-PORT",
        },
        "open_common_port": {
            "name": "open_common_port",
            "description": "Checks for open common ports",
            "object_type": "ipport",
            "query": f'(protocol = "TCP" and port in ({", ".join(str(x) for x in ALL_COMMON_TCP)})) '
            f'or (protocol = "UDP" and port in ({", ".join(str(x) for x in COMMON_UDP_PORTS)}))',
            "finding_type_code": "KAT-COMMON-OPEN-PORT",
        },
        "missing_caa": {
            "name": "missing_caa",
            "description": "Checks if a hostname has a CAA record",
            "object_type": "hostname",
            "query": "dnscaarecord = None",
            "finding_type_code": "KAT-NO-CAA",
        },
        "missing_dmarc": {
            "name": "missing_dmarc",
            "description": "Checks is mail servers have DMARC records",
            "object_type": "hostname",
            "query": f"""
            SELECT
                h.*
            FROM {Hostname._meta.db_table} h
            LEFT JOIN {Hostname._meta.db_table} root_h ON
                root_h.network_id = h.network_id
                    AND root_h.root = true
                    AND (h.name = root_h.name OR h.name LIKE '%%.' || root_h.name)
            LEFT JOIN {DNSTXTRecord._meta.db_table} direct_dmarc ON
                direct_dmarc.hostname_id = h._id
                    AND direct_dmarc.prefix = '_dmarc'
                    AND direct_dmarc.value LIKE 'v=DMARC1%%'
            LEFT JOIN {DNSTXTRecord._meta.db_table} root_dmarc ON
                root_dmarc.hostname_id = root_h._id
                    AND root_dmarc.prefix = '_dmarc' AND root_dmarc.value LIKE 'v=DMARC1%%'
            where direct_dmarc._id is null and root_dmarc._id is null
        """,  # noqa: S608
            "finding_type_code": "KAT-NO-DMARC",
        },
        "domain_owner_verification": {
            "name": "domain_owner_verification",
            "description": "Checks if the hostname has pending ownership",
            "object_type": "hostname",
            "query": f"dnsnsrecord_nameserver.name_server.name in ({', '.join(f'"{x}"' for x in INDICATORS)})",
            "finding_type_code": "KAT-DOMAIN-OWNERSHIP-PENDING",
        },
    }

    return BUSINESS_RULES


class HostnameQLSchema(DjangoQLSchema):
    """Custom schema to support nameservers_with_ipv6_count field for Hostname queries"""

    def get_fields(self, model):
        fields = super().get_fields(model)
        if model == Hostname:
            fields += [IntField(name="nameservers_with_ipv6_count")]
        return fields


def run_rules(rules: Sequence[BusinessRule], dry_run: bool = False) -> None:
    total_findings = 0

    for rule in rules:
        logger.info("\nProcessing rule: %s", rule.name)
        logger.info("Object Type: %s", rule.object_type)
        logger.info("Query: %s", rule.query)
        logger.info("Finding Type: %s", rule.finding_type_code)

        try:
            # Get the model class
            model_class = rule.object_type.model_class()
            if not model_class:
                logger.error("Unknown object type: %s", rule.object_type)
                continue

            # Get or create the finding type
            finding_type, created = FindingType.objects.get_or_create(code=rule.finding_type_code)
            if created:
                logger.info("Created new finding type: %s", rule.finding_type_code)

            # Build the queryset
            queryset = model_class.objects.all()

            # Special handling for Hostname queries that need annotations
            if model_class == Hostname and "nameservers_with_ipv6_count" in rule.query:
                queryset = queryset.annotate(
                    nameservers_with_ipv6_count=Count(
                        Case(
                            When(
                                dnsnsrecord__name_server__dnsaaaarecord__isnull=False,
                                then=F("dnsnsrecord__name_server_id"),
                            ),
                            default=None,
                        ),
                        distinct=True,
                    )
                )
                schema = HostnameQLSchema
            else:
                schema = DjangoQLSchema

            # Apply the query
            try:
                matching_objects = apply_search(queryset, rule.query, schema)
                match_count = matching_objects.count()
            except DjangoQLParserError:
                matching_objects = queryset.raw(rule.query)
                match_count = len(matching_objects)

            logger.info("Matching objects: %s", match_count)

            if dry_run:
                logger.warning("  [DRY RUN] Skipping finding creation")
                continue

            # Create findings for matching objects
            findings_created = 0
            findings = []
            existing = set(
                Finding.objects.filter(
                    finding_type=finding_type,
                    object_type=rule.object_type.model_class().__name__.lower(),
                    object_id__in=[obj.pk for obj in matching_objects],
                ).values_list("object_id", flat=True)
            )

            for obj in matching_objects:
                if obj.id in existing:
                    continue
                findings.append(
                    Finding(
                        finding_type=finding_type,
                        object_type=rule.object_type.model_class().__name__.lower(),
                        object_id=obj.pk,
                    )
                )

            bulk_insert(findings)
            findings_created += len(findings)

            logger.info("Created %s new findings", findings_created)
            total_findings += findings_created
        except Exception:
            logger.exception("Error processing business rule %s", rule.name)

    if dry_run:
        logger.warning("\n[DRY RUN] Would have created findings for %s objects", total_findings)
    else:
        logger.info("\nCompleted! Created %s new findings", total_findings)
