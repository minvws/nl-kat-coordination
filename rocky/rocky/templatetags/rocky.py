from django import template
from django.forms.widgets import MultipleHiddenInput

register = template.Library()


@register.filter
def is_multiple_hidden(field):
    return isinstance(field.field.widget, MultipleHiddenInput)
