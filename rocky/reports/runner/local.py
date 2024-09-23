from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from katalogus.client import Boefje
from tools.models import Organization

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.reports import ReportRecipe
from reports.report_types.definitions import BaseReport
from reports.report_types.helpers import get_report_by_id
from reports.runner.runtime_interfaces import ReportJobRunner
from reports.views.base import get_report_plugins_from_katalogus
from reports.views.mixins import collect_reports, save_report_data
from rocky.bytes_client import get_bytes_client


def get_plugins_from_report_type(report_types: list[type[BaseReport]], organization_code: str):
    # Duplicated from reports/views/base.py for now, until we find a meaningful abstraction
    plugins: dict[str, Any] = {"required": set(), "optional": set()}

    for report_type in report_types:
        for required_optional, report_type_plugin_ids in report_type.plugins.items():
            plugins[required_optional].update(report_type_plugin_ids)  # also removes duplicates

    # remove optional plugins that is also in the set of required plugins
    for plugin_id in plugins["required"]:
        if plugin_id in plugins["optional"]:
            plugins["optional"].remove(plugin_id)

    return get_report_plugins_from_katalogus(plugins, organization_code)


def get_plugin_data_for_saving(report_types: list[type[BaseReport]], organization_code: str):
    plugin_data = []
    report_type_plugins = get_plugins_from_report_type(report_types, organization_code)

    if report_type_plugins is not None:
        for required_optional, plugins in report_type_plugins.items():
            for plugin in plugins:
                plugin_data.append(
                    {
                        "required": required_optional == "required",
                        "enabled": plugin.enabled,
                        "name": plugin.name,
                        "scan_level": plugin.scan_level.value if isinstance(plugin, Boefje) else 0,
                        "type": plugin.type,
                        "description": plugin.description,
                    }
                )

    return plugin_data


class LocalReportJobRunner(ReportJobRunner):
    def run(self, recipe: ReportRecipe) -> None:
        now = datetime.now(timezone.utc)
        parsed_report_types = [get_report_by_id(report_type_id) for report_type_id in recipe.report_types]
        connector = OctopoesAPIConnector(settings.OCTOPOES_API, recipe.organization_code)

        error_reports, report_data = collect_reports(
            now,
            connector,
            list(recipe.input_recipe.values()),  # TODO: check
            parsed_report_types,
        )

        # TODO: KATalogusError
        save_report_data(
            get_bytes_client(recipe.organization_code),
            now,
            connector,
            Organization.objects.get(code=recipe.organization_code),
            get_plugin_data_for_saving(parsed_report_types, recipe.organization_code),
            report_data,
            recipe.report_names,
        )
