from django import template

from tasks.models import ObjectSet

register = template.Library()


@register.filter
def get_object_set(object_set_id):
    """Get ObjectSet by ID"""
    if not object_set_id:
        return None
    try:
        return ObjectSet.objects.get(pk=object_set_id)
    except ObjectSet.DoesNotExist:
        return None
