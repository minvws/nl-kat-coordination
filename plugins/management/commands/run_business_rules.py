import logging

from django.core.management import BaseCommand

from plugins.models import BusinessRule
from plugins.plugins.business_rules import run_rules

logger = logging.getLogger(__name__)


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
            logger.info(self.style.WARNING("No enabled business rules found"))
            return

        run_rules(rules, dry_run)
