from django import template

register = template.Library()


@register.filter
def to_class_name(model: object) -> str:
    return model.__class__.__name__
