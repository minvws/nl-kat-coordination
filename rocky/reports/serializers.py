from rest_framework import serializers

from rocky.views.mixins import HydratedReport


class ReportSerializer(serializers.BaseSerializer):
    def to_representation(self, instance):
        if isinstance(instance, HydratedReport):
            report = instance.parent_report
        else:
            report = instance
        return {
            "id": report.report_id,
            "valid_time": report.observed_at,
            "name": report.name,
            "report_type": report.report_type,
            "generated_at": report.date_generated,
            "intput_oois": report.input_oois,
        }


class ReportRecipeSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="recipe_id", read_only=True)
    report_name_format = serializers.CharField()
    asset_report_name_format = serializers.CharField(required=False)

    input_recipe = serializers.DictField()
    asset_report_types = serializers.ListField(child=serializers.CharField())

    cron_expression = serializers.CharField()
    start_date = serializers.DateField(write_only=True, required=False)
