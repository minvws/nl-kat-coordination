import logging

from django.core.management import BaseCommand
from django.db.models import Case, Count, F, When
from djangoql.queryset import apply_search
from djangoql.schema import DjangoQLSchema, IntField

from objects.models import Finding, FindingType, Hostname
from plugins.models import BusinessRule

logger = logging.getLogger(__name__)


class HostnameQLSchema(DjangoQLSchema):
    """Custom schema to support nameservers_with_ipv6_count field for Hostname queries"""

    def get_fields(self, model):
        fields = super().get_fields(model)
        if model == Hostname:
            fields += [IntField(name="nameservers_with_ipv6_count")]
        return fields


class Command(BaseCommand):
    help = "Run all enabled business rules and create findings for matching objects"

    def add_arguments(self, parser):
        parser.add_argument("--rule", "-r", type=str, help="Run only the specified business rule by name")
        parser.add_argument("--dry-run", "-d", action="store_true", help="Run without creating findings")

    def handle(self, *args, **options):
        rule_name = options.get("rule")
        dry_run = options.get("dry_run", False)

        if rule_name:
            rules = BusinessRule.objects.filter(name=rule_name, enabled=True)
            if not rules.exists():
                self.stdout.write(self.style.ERROR(f"Business rule '{rule_name}' not found or not enabled"))
                return
        else:
            rules = BusinessRule.objects.filter(enabled=True)

        if not rules.exists():
            self.stdout.write(self.style.WARNING("No enabled business rules found"))
            return

        total_findings = 0

        for rule in rules:
            self.stdout.write(f"\nProcessing rule: {rule.name}")
            self.stdout.write(f"  Object Type: {rule.object_type}")
            self.stdout.write(f"  Query: {rule.query}")
            self.stdout.write(f"  Finding Type: {rule.finding_type_code}")

            try:
                # Get the model class
                model_class = rule.object_type.model_class()
                if not model_class:
                    self.stdout.write(self.style.ERROR(f"  Unknown object type: {rule.object_type}"))
                    continue

                # Get or create the finding type
                finding_type, created = FindingType.objects.get_or_create(code=rule.finding_type_code)
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  Created new finding type: {rule.finding_type_code}"))

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
                matching_objects = apply_search(queryset, rule.query, schema)
                match_count = matching_objects.count()

                self.stdout.write(f"  Matching objects: {match_count}")

                if dry_run:
                    self.stdout.write(self.style.WARNING("  [DRY RUN] Skipping finding creation"))
                    continue

                # Create findings for matching objects
                findings_created = 0
                for obj in matching_objects:
                    finding, created = Finding.objects.get_or_create(
                        finding_type=finding_type,
                        object_type=rule.object_type.model_class().__name__.lower(),
                        object_id=obj.pk,
                    )
                    if created:
                        findings_created += 1

                self.stdout.write(self.style.SUCCESS(f"  Created {findings_created} new findings"))
                total_findings += findings_created

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error processing rule: {str(e)}"))
                logger.exception("Error processing business rule %s", rule.name)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"\n[DRY RUN] Would have created findings for {total_findings} objects")
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"\nCompleted! Created {total_findings} new findings"))
