from datetime import datetime, timezone

from django import forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from tools.forms.base import BaseRockyForm, DataListInput


class UploadRawForm(BaseRockyForm):
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

    ooi_id = forms.CharField(
        label="Scan OOI",
        widget=DataListInput(attrs={"placeholder": _("Click to select one of the available options")}),
    )

    def clean_mime_types(self) -> set[str]:
        mime_types = self.cleaned_data["mime_types"]

        return {mime_type.strip() for mime_type in mime_types.split(",") if mime_type.strip()}

    def __init__(
        self,
        connector: OctopoesAPIConnector,
        ooi_list: list[tuple[str, str]],
        *args,
        **kwargs,
    ):
        self.octopoes_connector = connector
        super().__init__(*args, **kwargs)
        self.set_choices_for_widget("ooi_id", ooi_list)

    def clean_ooi_id(self):
        try:
            data = self.cleaned_data["ooi_id"]
            self.octopoes_connector.get(Reference.from_str(data), datetime.now(timezone.utc))
            return data
        except ObjectNotFoundException:
            raise ValidationError(_("OOI doesn't exist"))
