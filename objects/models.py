import tempfile
from collections.abc import Sequence
from enum import Enum
from functools import total_ordering
from typing import cast

import structlog
import tagulous.models
from django.apps import apps
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import connections, models
from django.db.models import Case, CharField, ForeignKey, Manager, Model, OuterRef, Subquery, When
from django.db.models.expressions import RawSQL
from django.forms.models import model_to_dict
from django.utils.datastructures import CaseInsensitiveMapping
from django.utils.translation import gettext_lazy as _
from psycopg import DatabaseError, sql
from tldextract import tldextract
from transit.writer import Writer

from openkat.models import ORGANIZATION_CODE_LENGTH, LowerCaseCharField, LowerCaseSlugField

logger = structlog.get_logger(__name__)


def object_type_by_name() -> CaseInsensitiveMapping[type[models.Model]]:
    return CaseInsensitiveMapping({model.__name__: model for model in apps.get_app_config("objects").get_models()})


def to_xtdb_dict(model: Model) -> dict:
    mod = model_to_dict(model, exclude=["id"])
    mod["_id"] = model.pk

    if "_valid_from" in mod:
        del mod["_valid_from"]

    for field in model._meta.fields:
        if isinstance(field, ForeignKey):
            mod[field.name + "_id"] = mod[field.name]
            del mod[field.name]
            continue

    for mm_field in model._meta.many_to_many:
        mod[mm_field.name] = [item.id for item in mod[mm_field.name]]
        continue

    return mod


class ScanLevelEnum(models.IntegerChoices):
    L0 = 0, "L0"
    L1 = 1, "L1"
    L2 = 2, "L2"
    L3 = 3, "L3"
    L4 = 4, "L4"


MAX_SCAN_LEVEL = max(scan_level.value for scan_level in cast("type[Enum]", ScanLevelEnum))


class XTDBModel(models.Model):
    # This seems to be the only way to avoid Django trying to set the field in any instance, while still being able to
    # query the field.
    _valid_from: models.DateTimeField = models.GeneratedField(
        expression=RawSQL("_valid_from", ()), output_field=models.DateTimeField(), db_persist=False
    )

    class Meta:
        managed = False
        abstract = True

    @property
    def last_seen(self):
        return self._valid_from


class XTDBOrganizationTag(tagulous.models.TagTreeModel):
    COLOR_CHOICES = settings.TAG_COLORS
    BORDER_TYPE_CHOICES = settings.TAG_BORDER_TYPES

    color = models.CharField(choices=COLOR_CHOICES, max_length=20, default=COLOR_CHOICES[0][0])
    border_type = models.CharField(choices=BORDER_TYPE_CHOICES, max_length=20, default=BORDER_TYPE_CHOICES[0][0])

    class TagMeta:
        force_lowercase = True
        protect_all = True


class XTDBOrganization(XTDBModel):
    name = models.CharField(max_length=126, unique=True, help_text=_("The name of the organisation"))
    code = LowerCaseSlugField(
        max_length=ORGANIZATION_CODE_LENGTH,
        unique=True,
        allow_unicode=True,
        help_text=_(
            "A slug containing only lower-case unicode letters, numbers, hyphens or underscores "
            "that will be used in URLs and paths"
        ),
    )
    tags = tagulous.models.TagField(to=XTDBOrganizationTag, blank=True)

    def __str__(self) -> str:
        return str(self.name)


class Asset(XTDBModel):
    class Meta:
        managed = False
        abstract = True

    def delete(self, *args, **kwargs):
        try:
            Finding.objects.filter(object_id=self.pk).delete()
        except DatabaseError:
            logger.warning("Failed to delete Findings for %s", self)
        return super().delete(*args, **kwargs)


class ManagerWithGenericObjectForeignKey(Manager):
    """GenericForeignKey-like behavior. (We could consider writing a custom GenericForeignKey as well at one point.)"""

    def get_queryset(self):
        ref = OuterRef("object_id")

        return (
            super()
            .get_queryset()
            .annotate(
                object_human_readable=Case(
                    When(object_type="hostname", then=Subquery(Hostname.objects.filter(pk=ref).values("name"))),
                    When(object_type="ipaddress", then=Subquery(IPAddress.objects.filter(pk=ref).values("address"))),
                    When(object_type="network", then=Subquery(Network.objects.filter(pk=ref).values("name"))),
                    default=None,
                    output_field=CharField(),
                )
            )
        )


class FindingType(XTDBModel):
    code = models.CharField()
    name = models.CharField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    source = models.CharField(null=True, blank=True)
    risk = models.CharField(null=True, blank=True)
    impact = models.TextField(null=True, blank=True)
    recommendation = models.TextField(null=True, blank=True)
    score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(10.0)], null=True)

    class Meta:
        managed = False


class Finding(XTDBModel):
    finding_type: models.ForeignKey = models.ForeignKey(FindingType, on_delete=models.PROTECT)

    object_type: LowerCaseCharField = LowerCaseCharField()
    object_id: models.PositiveBigIntegerField = models.PositiveBigIntegerField()
    organizations = models.ManyToManyField(
        XTDBOrganization, blank=True, related_name="findings", through="FindingOrganization"
    )
    objects = ManagerWithGenericObjectForeignKey()

    class Meta:
        managed = False


class FindingOrganization(XTDBModel):
    finding: models.ForeignKey = models.ForeignKey(Finding, on_delete=models.PROTECT)
    organization: models.ForeignKey = models.ForeignKey(XTDBOrganization, on_delete=models.PROTECT)


class Network(Asset):
    name: LowerCaseCharField = LowerCaseCharField()
    scan_level: models.IntegerField = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(MAX_SCAN_LEVEL)], null=True, blank=True
    )
    declared: models.BooleanField = models.BooleanField(default=False)
    organizations = models.ManyToManyField(
        XTDBOrganization, blank=True, related_name="networks", through="NetworkOrganization"
    )

    def __str__(self) -> str:
        return self.name


class NetworkOrganization(XTDBModel):
    network: models.ForeignKey = models.ForeignKey(Network, on_delete=models.PROTECT)
    organization: models.ForeignKey = models.ForeignKey(XTDBOrganization, on_delete=models.PROTECT)


class IPAddress(Asset):
    network: models.ForeignKey = models.ForeignKey(Network, on_delete=models.CASCADE)
    address: models.GenericIPAddressField = models.GenericIPAddressField(unpack_ipv4=True)
    scan_level: models.IntegerField = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(MAX_SCAN_LEVEL)], null=True, blank=True
    )
    declared: models.BooleanField = models.BooleanField(default=False)
    organizations = models.ManyToManyField(
        XTDBOrganization, blank=True, related_name="ipaddresses", through="IPAddressOrganization"
    )

    def __str__(self) -> str:
        return self.address


class IPAddressOrganization(XTDBModel):
    ipaddress: models.ForeignKey = models.ForeignKey(IPAddress, on_delete=models.PROTECT)
    organization: models.ForeignKey = models.ForeignKey(XTDBOrganization, on_delete=models.PROTECT)


class Protocol(models.TextChoices):
    TCP = "TCP", "TCP"
    UDP = "UDP", "UDP"


class IPPort(XTDBModel):
    address: models.ForeignKey = models.ForeignKey(IPAddress, on_delete=models.CASCADE)
    protocol: models.CharField = models.CharField(choices=Protocol)
    port: models.IntegerField = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(65535)])
    tls: models.BooleanField = models.BooleanField(null=True)
    service: models.CharField = models.CharField()

    class Meta:
        managed = False

    def __str__(self) -> str:
        return f"[{self.address}]:{self.port}"


class Hostname(Asset):
    dnsarecord_set: models.Manager["DNSARecord"]
    dnsaaaarecord_set: models.Manager["DNSAAAARecord"]
    dnscnamerecord_set: models.Manager["DNSCNAMERecord"]
    dnsmxrecord_set: models.Manager["DNSMXRecord"]
    dnsnsrecord_set: models.Manager["DNSNSRecord"]
    dnsptrrecord_set: models.Manager["DNSPTRRecord"]
    dnscaarecord_set: models.Manager["DNSCAARecord"]
    dnstxtrecord_set: models.Manager["DNSTXTRecord"]
    dnssrvrecord_set: models.Manager["DNSSRVRecord"]
    dnscnamerecord_target_set: models.Manager["DNSCNAMERecord"]
    dnsmxrecord_mailserver: models.Manager["DNSMXRecord"]
    dnsnsrecord_nameserver: models.Manager["DNSNSRecord"]

    class Q:
        """A set of useful DjangoQL queries for Hostname"""

        mail_server = "dnsmxrecord_mailserver != None"
        name_server = "dnsnsrecord_nameserver != None"
        root_domain = "root = True"

    network: models.ForeignKey = models.ForeignKey(Network, on_delete=models.CASCADE)
    name: LowerCaseCharField = LowerCaseCharField()
    root: models.BooleanField = models.BooleanField(default=False)
    scan_level: models.IntegerField = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(MAX_SCAN_LEVEL)], null=True, blank=True
    )
    declared: models.BooleanField = models.BooleanField(default=False)
    organizations = models.ManyToManyField(
        XTDBOrganization, blank=True, related_name="hostnames", through="HostnameOrganization"
    )

    def __str__(self) -> str:
        if self.name is None:  # TODO: fix, this  can happen for some reason...
            return ""

        return self.name

    def save(self, *args, **kwargs):
        if self.name:
            extracted = tldextract.extract(self.name)
            registered_domain = extracted.top_domain_under_public_suffix.rstrip(".")
            self.root = self.name == registered_domain

            # If this is a subdomain, ensure the root domain exists
            if not self.root and registered_domain:
                root_hostname, created = Hostname.objects.get_or_create(
                    network=self.network, name=registered_domain, defaults={"root": True}
                )
                # Ensure root flag is set correctly if it already existed
                if not created and not root_hostname.root:
                    root_hostname.root = True
                    root_hostname.save(update_fields=["root"])

        super().save(*args, **kwargs)


class HostnameOrganization(XTDBModel):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.PROTECT)
    organization: models.ForeignKey = models.ForeignKey(XTDBOrganization, on_delete=models.PROTECT)


class DNSRecordBase(XTDBModel):
    ttl: models.IntegerField = models.IntegerField()

    class Meta:
        managed = False
        abstract = True


class DNSARecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.CASCADE)
    ip_address: models.ForeignKey = models.ForeignKey(IPAddress, on_delete=models.PROTECT)

    hostname_id: int | None

    def __str__(self) -> str:
        return f"{self.hostname} A {self.ip_address}"


class DNSAAAARecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.CASCADE)
    ip_address: models.ForeignKey = models.ForeignKey(IPAddress, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return f"{self.hostname} AAAA {self.ip_address}"


class DNSPTRRecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.CASCADE)
    ip_address: models.ForeignKey = models.ForeignKey(IPAddress, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return f"{self.ip_address} PTR {self.hostname}"


class DNSCNAMERecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.CASCADE)
    target: models.ForeignKey = models.ForeignKey(
        Hostname, on_delete=models.PROTECT, related_name="dnscnamerecord_target_set"
    )

    def __str__(self) -> str:
        return f"{self.hostname} CNAME {self.target}"


class DNSMXRecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.CASCADE)
    mail_server: models.ForeignKey = models.ForeignKey(
        Hostname, on_delete=models.PROTECT, related_name="dnsmxrecord_mailserver"
    )
    preference: models.IntegerField = models.IntegerField()

    def __str__(self) -> str:
        return f"{self.hostname} MX {self.preference} {self.mail_server}"


class DNSNSRecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.CASCADE)
    name_server: models.ForeignKey = models.ForeignKey(
        Hostname, on_delete=models.PROTECT, related_name="dnsnsrecord_nameserver"
    )

    def __str__(self) -> str:
        return f"{self.hostname} NS {self.name_server}"


class CAATag(models.TextChoices):
    CONTACTEMAIL = "contactemail", "contactemail"
    CONTACTPHONE = "contactphone", "contactphone"
    IODEF = "iodef", "iodef"
    ISSUE = "issue", "issue"
    ISSUEMAIL = "issuemail", "issuemail"
    ISSUEVMC = "issuevmc", "issuevmc"
    ISSUEWILD = "issuewild", "issuewild"


class DNSCAARecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.CASCADE)
    flags: models.IntegerField = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(255)])
    tag: models.CharField = models.CharField(choices=CAATag)
    value: models.CharField = models.CharField()

    def __str__(self) -> str:
        return f"{self.hostname} CAA {self.flags} {self.tag} {self.value}"


class DNSTXTRecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.CASCADE)
    prefix: models.CharField = models.CharField(blank=True)
    value: models.CharField = models.CharField()

    def __str__(self) -> str:
        prefix_part = f"{self.prefix}." if self.prefix else ""
        return f"{prefix_part}{self.hostname} TXT {self.value}"


class DNSSRVRecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.CASCADE)
    proto: LowerCaseCharField = LowerCaseCharField()
    service: LowerCaseCharField = LowerCaseCharField()
    priority: models.IntegerField = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(65535)])
    weight: models.IntegerField = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(65535)])
    port: models.IntegerField = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(65535)])

    def __str__(self) -> str:
        return f"_{self.service}._{self.proto}.{self.hostname} SRV {self.priority} {self.weight} {self.port}"


class Software(XTDBModel):
    name = models.CharField()
    version = models.CharField(null=True, blank=True)
    cpe = models.CharField(null=True, blank=True)
    ports = models.ManyToManyField(IPPort, blank=True, related_name="software")


def bulk_insert(objects: Sequence[models.Model]) -> None:
    """Use COPY to efficiently bulk-insert objects into XTDB. Assumes objects have the same type, skips other types."""

    if not objects:
        return

    table_name = objects[0]._meta.db_table

    with tempfile.NamedTemporaryFile() as fp:
        # The transit-json format is not working because the writer uses a comma as a delimiter between objects. It
        # would work if we override Writer.marshaler.write_sep() to skip the comma (or use a newline) between objects.
        # But apparently msgpack works out of the box, which makes life even easier.

        writer = Writer(fp, "msgpack")
        for obj in objects:
            if obj._meta.db_table != table_name:
                continue
            writer.write(to_xtdb_dict(obj))

        fp.seek(0)

        with (
            connections["xtdb"].cursor() as cursor,
            cursor.copy(
                sql.SQL("COPY {} FROM STDIN WITH (FORMAT 'transit-msgpack')").format(sql.Identifier(table_name))
            ) as copy,
        ):
            while data := fp.read():
                copy.write(data)


severity_order = ["recommendation", "low", "medium", "high", "critical"]


@total_ordering
class RiskLevelSeverity(Enum):
    """Represents the risk level severity of findings"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    RECOMMENDATION = "recommendation"

    def __gt__(self, other: "RiskLevelSeverity") -> bool:
        return severity_order.index(self.value) > severity_order.index(other.value)

    def __str__(self) -> str:
        return self.value


SEVERITY_SCORE_LOOKUP = {
    RiskLevelSeverity.CRITICAL.value: 10.0,
    RiskLevelSeverity.HIGH.value: 8.9,
    RiskLevelSeverity.MEDIUM.value: 6.9,
    RiskLevelSeverity.LOW.value: 3.9,
    RiskLevelSeverity.RECOMMENDATION.value: 0.0,
}
