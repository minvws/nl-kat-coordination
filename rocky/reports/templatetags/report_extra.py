from django import template

register = template.Library()


@register.filter
def sum_attribute(checks, attribute):
    return sum(getattr(check, attribute) for check in checks if hasattr(check, attribute))
