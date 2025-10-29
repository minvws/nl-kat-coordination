import json
from datetime import datetime
from typing import Any
from urllib import parse

from django import template

register = template.Library()


@register.filter
def get_encoded_dict(data_dict: dict) -> str:
    return parse.urlencode(data_dict)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_key(array, key):
    return [x[key] for x in array]


@register.filter
def sum_list(array):
    return sum(array)


@register.simple_tag()
def get_scan_levels() -> list[str]:
    return list(map(str, range(1, 5)))


@register.filter()
def get_type(x: Any) -> Any:
    return type(x).__name__


@register.filter()
def get_type_name(instance):
    return type(instance).__name__


@register.simple_tag(takes_context=True)
def url_replace(context, field, value):
    dict_ = context["request"].GET.copy()
    dict_[field] = value
    return dict_.urlencode()


@register.filter
def index(indexable, i):
    return indexable[i]


@register.filter
def pretty_json(obj: dict) -> str:
    return json.dumps(obj, default=str, indent=4)


@register.filter
def get_datetime(date_str: str) -> datetime:
    return datetime.fromisoformat(date_str)


@register.filter
def get_first_seen(occurrences: dict) -> datetime:
    first_seen = min(occurrences, key=lambda occurrence: occurrence["first_seen"])["first_seen"]
    return datetime.fromisoformat(first_seen)


@register.filter
def with_form_attr(field, form_id):
    return field.as_widget(attrs={"form": form_id})
