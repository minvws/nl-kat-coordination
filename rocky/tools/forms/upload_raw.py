from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _


class UploadRawForm(forms.Form):
    mime_types = forms.CharField(
        label=_("Mime types"),
        help_text=mark_safe(
            _(
                '<p>Add a set of mime types, separated by commas, for example:</p><p><i>"text/html, image/jpeg"</i> or '
                '<i>"boefje/dns-records"</i>.</p><p>Mime types are used to match the correct normalizer to a raw file. '
                'When the mime type "boefje/dns-records" is added, the normalizer expects the raw file to contain dns '
                "scan information.</p>"
            )
        ),
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "text/html, image/jpeg, ..."}),
    )
    raw_file = forms.FileField(
        label=_("Upload raw file"),
        allow_empty_file=False,
    )

    def clean_mime_types(self) -> set[str]:
        mime_types = self.cleaned_data["mime_types"]

        return set([mime_type.strip() for mime_type in mime_types.split(",") if mime_type.strip()])
