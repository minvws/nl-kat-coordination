# Django Modal Component

## Goal

The goal of this Modal Component is to have a "one stop shop" solution for a modal dialog, with the HTML structure as a template, CSS styling in SASS, JS logic for its dynamics and Django for all data related logic all bundled into one solution. Utilizing the `django-component` third-party library, it enables us to implement modals easily in Django templates, wherever they're needed. By using `slot` and `fill` we have great content flexibility, while keeping the aforementioned topics like HTML structure, CSS and JS as DRY as possible.

## Usage

This outlines the basic usages and provides a code block example below, of how to implement the component in a Django template.

### Instantiate

First you need to add `{% load component_tags %}` at the top of your template. Next you need to add the following code block at the bottom, to include the corresponding JS (if you haven't already you also need to add `{% load compress %}`).

```
{% block html_at_end_body %}
    {{ block.super }}
    {% compress js %}
        <script src="{% static "modal/script.js" %}" nonce="{{ request.csp_nonce }}" type="module"></script>
    {% endcompress %}
{% endblock html_at_end_body %}
```

After that, `{% component "modal" size="xx" dialogid="xx" %}` is enough to instantiate the dialog modal component, where `dialogid` should be a unique identifier to enable multiple dialogs on the same page, and size should contain the appropriate class name to achieve the correct sizing. This can be either `dialog-small`, `dialog-medium` or `dialog-large`.

### Slots and fills

Each named `fill` corresponds with a placeholder/target `slot` in the component template. The contents between the `fill` tag will be passed to the corresponding `slot`. As shown in the below example it's possible to utilise Django template tags and `HTML` tags with these `fill` tags. This enables us to entirely build the contents of the modal in the template where we implement it. Because we can use `HTML` tags here, we can also use `forms` and leave the handling of said form up to the Django template that knows about the context and applicable data, where we implement the modal. The defaults are used when no `fill` tags are implemented for this slot at all.

There's three slots to fill:

1.  `header`: empty by default
2.  `content`: empty by default
3.  `footer_buttons`: _cancel button_ by default. To have _no buttons_ show at all, it's needed to implement empty `fill` tags for this `slot`.

### CSS dependencies

Including `{% component_css_dependencies %}` is needed to inject the reference to the correct stylesheet needed to style the component into the HTML document. Configuring the location of said stylesheet is done in the components `.py` file.

```
{% component "modal" size="dialog-small" dialogid="id1" %}
	{% fill "header" %}
		{% translate "This is an example header." %}
	{% endfill %}
	{% fill "content" %}
		<form  id="content-form"  class="horizontal-view"  action=""  method="post">
			{% csrf_token %}
			{% blocktranslate %}
				<p>You can use {{ context_data_variable }} and HTML here <code>valid_time</code>!</p>
			{% endblocktranslate %}
		</form>
	{% endfill %}
	{% fill "footer_buttons" %}
		<input  type="submit"  form="content-form"  class="submit"  value="Submit">
	{% endfill %}
{% endcomponent %}
{% component_css_dependencies %}
```
