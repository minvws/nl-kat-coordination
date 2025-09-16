from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from oois.enums import MAX_SCAN_LEVEL
from openkat.models import LowerCaseCharField, Organization


class Asset(models.Model):
    class Meta:
        managed = False
        abstract = True


class ScanLevel(models.Model):
    id: int
    ooi_type: models.ForeignKey = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    ooi_id: models.PositiveBigIntegerField = models.PositiveBigIntegerField()
    ooi: GenericForeignKey = GenericForeignKey("ooi_type", "ooi_id")
    organization: models.ForeignKey = models.ForeignKey(
        Organization, on_delete=models.PROTECT
    )
    scan_level: models.IntegerField = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(MAX_SCAN_LEVEL)]
    )
    declared: models.BooleanField = models.BooleanField(default=False)
    last_changed_by: models.ForeignKey = models.ForeignKey(
        "account.KATUser", on_delete=models.PROTECT, null=True, blank=True
    )

    class Meta:
        managed = False

    def __str__(self) -> str:
        return str(self.id)


class Network(Asset):
    name: LowerCaseCharField = LowerCaseCharField()

    def __str__(self) -> str:
        return self.name


class IPAddress(Asset):
    network: models.ForeignKey = models.ForeignKey(Network, on_delete=models.PROTECT)
    address: models.GenericIPAddressField = models.GenericIPAddressField(unpack_ipv4=True)

    def __str__(self) -> str:
        return self.address


class Protocol(models.TextChoices):
    TCP = "TCP", "TCP"
    UDP = "UDP", "UDP"


class IPPort(models.Model):
    address: models.ForeignKey = models.ForeignKey(IPAddress, on_delete=models.PROTECT)
    protocol: models.CharField = models.CharField(choices=Protocol)
    port: models.IntegerField = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(65535)]
    )
    tls: models.BooleanField = models.BooleanField(null=True)
    service: models.CharField = models.CharField()

    class Meta:
        managed = False

    def __str__(self) -> str:
        return f"[{self.address}]:{self.port}"


class Hostname(Asset):
    network: models.ForeignKey = models.ForeignKey(Network, on_delete=models.PROTECT)
    name: LowerCaseCharField = LowerCaseCharField()

    def __str__(self) -> str:
        return self.name


class DNSRecordBase(models.Model):
    ttl: models.IntegerField = models.IntegerField()

    class Meta:
        managed = False
        abstract = True


class DNSARecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.PROTECT)
    ip_address: models.ForeignKey = models.ForeignKey(IPAddress, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return f"{self.hostname} A {self.ip_address}"


class DNSAAAARecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.PROTECT)
    ip_address: models.ForeignKey = models.ForeignKey(IPAddress, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return f"{self.hostname} AAAA {self.ip_address}"


class DNSPTRRecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.PROTECT)
    ip_address: models.ForeignKey = models.ForeignKey(IPAddress, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return f"{self.ip_address} PTR {self.hostname}"


class DNSCNAMERecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(
        Hostname, on_delete=models.PROTECT, related_name="cname_records"
    )
    target: models.ForeignKey = models.ForeignKey(
        Hostname, on_delete=models.PROTECT, related_name="cname_targets"
    )

    def __str__(self) -> str:
        return f"{self.hostname} CNAME {self.target}"


class DNSMXRecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(
        Hostname, on_delete=models.PROTECT, related_name="mx_records"
    )
    mail_server: models.ForeignKey = models.ForeignKey(
        Hostname, on_delete=models.PROTECT, related_name="mx_targets"
    )
    preference: models.IntegerField = models.IntegerField()

    def __str__(self) -> str:
        return f"{self.hostname} MX {self.preference} {self.mail_server}"


class DNSNSRecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(
        Hostname, on_delete=models.PROTECT, related_name="ns_records"
    )
    name_server: models.ForeignKey = models.ForeignKey(
        Hostname, on_delete=models.PROTECT, related_name="ns_targets"
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
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.PROTECT)
    flags: models.IntegerField = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(255)]
    )
    tag: models.CharField = models.CharField(choices=CAATag)
    value: models.CharField = models.CharField()

    def __str__(self) -> str:
        return f"{self.hostname} CAA {self.flags} {self.tag} {self.value}"


class DNSTXTRecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.PROTECT)
    prefix: models.CharField = models.CharField(blank=True)
    value: models.CharField = models.CharField()

    def __str__(self) -> str:
        prefix_part = f"{self.prefix}." if self.prefix else ""
        return f"{prefix_part}{self.hostname} TXT {self.value}"


class DNSSRVRecord(DNSRecordBase):
    hostname: models.ForeignKey = models.ForeignKey(Hostname, on_delete=models.PROTECT)
    proto: LowerCaseCharField = LowerCaseCharField()
    service: LowerCaseCharField = LowerCaseCharField()
    priority: models.IntegerField = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(65535)]
    )
    weight: models.IntegerField = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(65535)]
    )
    port: models.IntegerField = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(65535)]
    )

    def __str__(self) -> str:
        return f"_{self.service}._{self.proto}.{self.hostname} SRV {self.priority} {self.weight} {self.port}"
