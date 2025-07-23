from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def media_with_nonce(context):
    nonce = context["request"].csp_nonce
    return mark_safe(str(context["media"]).replace("<script src=", f'<script nonce="{nonce}" src='))


@register.simple_tag(takes_context=True)
def media_js_with_nonce(context):
    nonce = context["request"].csp_nonce
    return mark_safe(str(context["media"]["js"]).replace("<script src=", f'<script nonce="{nonce}" src='))
