import json
from typing import Any, List, Type, Set
from urllib import parse

from django import template
from django.utils.translation import gettext_lazy as _
from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, FindingType

from rocky.views import KATalogusListView
from tools.models import GROUP_REDTEAM, GROUP_ADMIN
from tools.view_helpers import get_ooi_url

register = template.Library()


@register.inclusion_tag("partials/form/single_action_form.html")
def enable_disable_boefje_button(boefje, has_permission):
    return {
        "action": KATalogusListView.PageActions.BOEFJE_DISABLE.value
        if boefje.enabled
        else KATalogusListView.PageActions.BOEFJE_ENABLE.value,
        "btn_text": _("Disable") if boefje.enabled else _("Enable"),
        "btn_class": "ghost" if boefje.enabled else None,
        "btn_disabled": not has_permission,
        "key": "boefje_id",
        "value": boefje.id,
    }


@register.filter
def get_encoded_dict(data_dict: dict):
    return parse.urlencode(data_dict)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.simple_tag()
def get_scan_levels() -> List[str]:
    return list(map(str, range(1, 5)))


@register.filter
def ooi_types_to_strings(ooi_types: Set[Type[OOI]]):
    return [ooi_type.get_ooi_type() for ooi_type in ooi_types]


@register.filter()
def get_type(x: Any):
    return type(x)


@register.simple_tag()
def ooi_url(routename: str, ooi_id: str, **kwargs) -> str:
    return get_ooi_url(routename, ooi_id, **kwargs)


@register.filter()
def is_finding(ooi: OOI):
    return isinstance(ooi, Finding)


@register.filter()
def is_finding_type(ooi: OOI):
    return isinstance(ooi, FindingType)


@register.filter()
def get_type_name(instance):
    return type(instance).__name__


@register.simple_tag(takes_context=True)
def user_belongs_to(context, group: str):
    user = context["request"].user
    return user.groups.filter(name=group).exists()


@register.simple_tag(takes_context=True)
def is_user_redteam(context, group: str):
    user = context["request"].user
    return user.groups.filter(name=GROUP_REDTEAM).exists()


@register.simple_tag(takes_context=True)
def is_user_admin(context, group: str):
    user = context["request"].user
    return user.groups.filter(name=GROUP_ADMIN).exists()


@register.simple_tag(takes_context=True)
def url_replace(context, field, value):
    dict_ = context["request"].GET.copy()
    dict_[field] = value
    return dict_.urlencode()


@register.filter
def index(indexable, i):
    return indexable[i]


@register.filter
def has_group(user, group: str):
    return user.groups.filter(name=group).exists()


@register.filter
def pretty_json(obj: dict):
    return json.dumps(obj, default=str, indent=4)
