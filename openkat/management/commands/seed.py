import logging

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand

from objects.models import Hostname, IPPort, Network
from openkat.models import GROUP_ADMIN, GROUP_CLIENT, GROUP_REDTEAM
from plugins.models import BusinessRule
from tasks.models import ObjectSet


class Command(BaseCommand):
    help = "Creates the development organization, member, groups and set permissions."

    def get_permissions(self, codenames):
        permission_objects = []
        if codenames:
            for codename in codenames:
                try:
                    permission = Permission.objects.get(codename=codename)
                except Permission.DoesNotExist:
                    raise ObjectDoesNotExist("Permission:" + codename + " does not exist.")
                else:
                    permission_objects.append(permission.id)

        return permission_objects

    def setup_kat_groups(self):
        self.group_admin, self.group_admin_created = Group.objects.get_or_create(name=GROUP_ADMIN)
        self.group_redteam, self.group_redteam_created = Group.objects.get_or_create(name=GROUP_REDTEAM)
        self.group_client, self.group_client_created = Group.objects.get_or_create(name=GROUP_CLIENT)

    def handle(self, *args, **options):
        self.setup_kat_groups()
        self.setup_group_permissions()
        Network.objects.get_or_create(name="internet")
        ObjectSet.objects.get_or_create(
            name="mail_server",
            description="Mail servers are hostnames that have an MX record pointed to them.",
            dynamic=True,
            object_type=ContentType.objects.get_for_model(Hostname),
            object_query=Hostname.Q.mail_server,
        )
        ObjectSet.objects.get_or_create(
            name="name_server",
            description="Name servers are hostnames that have an NS record pointed to them.",
            dynamic=True,
            object_type=ContentType.objects.get_for_model(Hostname),
            object_query=Hostname.Q.name_server,
        )
        ObjectSet.objects.get_or_create(
            name="root_domains",
            description="Root domains are hostnames that represent the registered domain (e.g., example.com).",
            dynamic=True,
            object_type=ContentType.objects.get_for_model(Hostname),
            object_query=Hostname.Q.root_domain,
        )
        self.seed_business_rules()

    def seed_business_rules(self):
        """Seed business rules from test_dns_rules.py"""
        # Get ContentType objects for the models we'll use
        hostname_ct = ContentType.objects.get_for_model(Hostname)
        ipport_ct = ContentType.objects.get_for_model(IPPort)

        # Port lists
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

        rules = [
            {
                "name": "ipv6_webservers",
                "description": "Checks if webserver has IPv6 support",
                "object_type": hostname_ct,
                "query": "dnsnsrecord_nameserver = None and dnsaaaarecord = None",
                "finding_type_code": "KAT-WEBSERVER-NO-IPV6",
            },
            {
                "name": "ipv6_nameservers",
                "description": "Checks if nameserver has IPv6 support",
                "object_type": hostname_ct,
                "query": "dnsnsrecord_nameserver != None and dnsaaaarecord = None",
                "finding_type_code": "KAT-NAMESERVER-NO-IPV6",
            },
            {
                "name": "two_ipv6_nameservers",
                "description": "Checks if a hostname has at least two nameservers supporting IPv6",
                "object_type": hostname_ct,
                "query": "dnsnsrecord_nameserver = None and nameservers_with_ipv6_count < 2",
                "finding_type_code": "KAT-NAMESERVER-NO-TWO-IPV6",
            },
            {
                "name": "missing_spf",
                "description": "Checks is the hostname has valid SPF records",
                "object_type": hostname_ct,
                "query": 'dnstxtrecord.value not startswith "v=spf1"',
                "finding_type_code": "KAT-NO-SPF",
            },
            {
                "name": "open_sysadmin_port",
                "description": "Detect open sysadmin ports",
                "object_type": ipport_ct,
                "query": f'protocol = "TCP" and port in ({", ".join(str(x) for x in SA_TCP_PORTS)})',
                "finding_type_code": "KAT-OPEN-SYSADMIN-PORT",
            },
            {
                "name": "open_database_port",
                "description": "Detect open database ports",
                "object_type": ipport_ct,
                "query": f'protocol = "TCP" and port in ({", ".join(str(x) for x in DB_TCP_PORTS)})',
                "finding_type_code": "KAT-OPEN-DATABASE-PORT",
            },
            {
                "name": "open_remote_desktop_port",
                "description": "Detect open RDP ports",
                "object_type": ipport_ct,
                "query": f'protocol = "TCP" and port in ({", ".join(str(x) for x in MICROSOFT_RDP_PORTS)})',
                "finding_type_code": "KAT-REMOTE-DESKTOP-PORT",
            },
            {
                "name": "open_uncommon_port",
                "description": "Detect open uncommon ports",
                "object_type": ipport_ct,
                "query": f'(protocol = "TCP" and port not in ({", ".join(str(x) for x in ALL_COMMON_TCP)})) '
                f'or (protocol = "UDP" and port not in ({", ".join(str(x) for x in COMMON_UDP_PORTS)}))',
                "finding_type_code": "KAT-UNCOMMON-OPEN-PORT",
            },
            {
                "name": "open_common_port",
                "description": "Checks for open common ports",
                "object_type": ipport_ct,
                "query": f'(protocol = "TCP" and port in ({", ".join(str(x) for x in ALL_COMMON_TCP)})) '
                f'or (protocol = "UDP" and port in ({", ".join(str(x) for x in COMMON_UDP_PORTS)}))',
                "finding_type_code": "KAT-COMMON-OPEN-PORT",
            },
            {
                "name": "missing_caa",
                "description": "Checks if a hostname has a CAA record",
                "object_type": hostname_ct,
                "query": "dnscaarecord = None",
                "finding_type_code": "KAT-NO-CAA",
            },
            {
                "name": "missing_dmarc",
                "description": "Checks is mail servers have DMARC records",
                "object_type": hostname_ct,
                "query": 'dnsmxrecord_mailserver != None and name startswith "_dmarc"',
                "finding_type_code": "KAT-NO-DMARC",
            },
            {
                "name": "domain_owner_verification",
                "description": "Checks if the hostname has pending ownership",
                "object_type": hostname_ct,
                "query": f"dnsnsrecord_nameserver.name_server.name in ({', '.join(f'"{x}"' for x in INDICATORS)})",
                "finding_type_code": "KAT-DOMAIN-OWNERSHIP-PENDING",
            },
        ]

        for rule_data in rules:
            BusinessRule.objects.update_or_create(
                name=rule_data["name"],
                defaults={
                    "description": rule_data["description"],
                    "enabled": True,
                    "finding_type_code": rule_data["finding_type_code"],
                    "object_type": rule_data["object_type"],
                    "query": rule_data["query"],
                },
            )

        logging.info("Business rules seeded successfully")

    def setup_group_permissions(self):
        redteamer_permissions = ["can_scan_organization", "can_set_clearance_level"]

        redteam_permissions = self.get_permissions(redteamer_permissions)
        self.group_redteam.permissions.set(redteam_permissions)

        admin_permissions = self.get_permissions(
            redteamer_permissions
            + [
                "view_organization",
                "view_organizationmember",
                "add_organizationmember",
                "change_organization",
                "can_scan_organization",
                "change_organizationmember",
                "add_indemnification",
            ]
        )
        self.group_admin.permissions.set(admin_permissions)

        client_permissions = self.get_permissions(["can_scan_organization"])
        self.group_client.permissions.set(client_permissions)

        logging.info("OPENKAT HAS BEEN SETUP SUCCESSFULLY")
