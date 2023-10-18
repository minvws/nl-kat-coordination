from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def feature_reports():
    return settings.FEATURE_REPORTS
