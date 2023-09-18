from django import template

register = template.Library()


@register.simple_tag
def build_querystring(request, extra_key, extra_value):
    querystring = request.GET.copy()
    querystring[extra_key] = extra_value
    new_querystring = ""
    for index, (key, value) in enumerate(querystring.items()):
        if index == 0:
            new_querystring += "?" + key + "=" + value
        else:
            new_querystring += "&" + key + "=" + value
    return new_querystring
