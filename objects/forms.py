import csv
import io

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from objects.models import Network
from openkat.forms.upload_csv import UploadCSVForm


class HostnameCSVUploadForm(UploadCSVForm):
    network = forms.ModelChoiceField(
        queryset=Network.objects.all(),
        required=False,
        label=_("Network"),
        help_text=_("Select network for all hostnames. Defaults to 'internet' network."),
    )

    def clean(self):
        cleaned_data = super().clean()
        csv_file = cleaned_data.get("csv_file")

        if csv_file:
            csv_raw_data = csv_file.read()
            csv_data = io.StringIO(csv_raw_data.decode("UTF-8"))
            csv_file.seek(0)  # Reset for later processing

            try:
                reader = csv.reader(csv_data, delimiter=",", quotechar='"')
                rows = list(reader)

                if not rows:
                    raise ValidationError(_("CSV file is empty."))

                # Check if each row has exactly 1 column
                for i, row in enumerate(rows, 1):
                    if len(row) != 1:
                        raise ValidationError(
                            _("Row {row_num} has {col_count} columns. Expected 1 column (name).").format(
                                row_num=i, col_count=len(row)
                            )
                        )

            except csv.Error as e:
                raise ValidationError(_("Error parsing CSV: {error}").format(error=str(e)))

        return cleaned_data


class IPAddressCSVUploadForm(UploadCSVForm):
    network = forms.ModelChoiceField(
        queryset=Network.objects.all(),
        required=False,
        label=_("Network"),
        help_text=_("Select network for all IP addresses. Defaults to 'internet' network."),
    )

    def clean(self):
        cleaned_data = super().clean()
        csv_file = cleaned_data.get("csv_file")

        if csv_file:
            csv_raw_data = csv_file.read()
            csv_data = io.StringIO(csv_raw_data.decode("UTF-8"))
            csv_file.seek(0)  # Reset for later processing

            try:
                reader = csv.reader(csv_data, delimiter=",", quotechar='"')
                rows = list(reader)

                if not rows:
                    raise ValidationError(_("CSV file is empty."))

                # Check if each row has exactly 1 column
                for i, row in enumerate(rows, 1):
                    if len(row) != 1:
                        raise ValidationError(
                            _("Row {row_num} has {col_count} columns. Expected 1 column (address).").format(
                                row_num=i, col_count=len(row)
                            )
                        )

            except csv.Error as e:
                raise ValidationError(_("Error parsing CSV: {error}").format(error=str(e)))

        return cleaned_data
