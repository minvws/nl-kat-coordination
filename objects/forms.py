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


class GenericAssetBulkCreateForm(forms.Form):
    """Form for bulk creating IP addresses and hostnames from textarea input."""

    assets = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10, "placeholder": "192.168.1.1\nexample.com\n10.0.0.1\ntest.org"}),
        label=_("IP Addresses or Hostnames"),
        help_text=_("Enter one IP address or hostname per line."),
        required=True,
    )
    network = forms.ModelChoiceField(
        queryset=Network.objects.all(),
        required=False,
        label=_("Network"),
        help_text=_("Select network for all assets. Defaults to 'internet' network."),
    )

    def clean_assets(self):
        assets = self.cleaned_data.get("assets", "")
        lines = [line.strip() for line in assets.splitlines() if line.strip()]

        if not lines:
            raise ValidationError(_("Please provide at least one IP address or hostname."))

        return lines


class GenericAssetCSVUploadForm(UploadCSVForm):
    """Form for CSV upload of IP addresses and hostnames with optional scan level and organization."""

    network = forms.ModelChoiceField(
        queryset=Network.objects.all(),
        required=False,
        label=_("Network"),
        help_text=_("Select default network for all assets. Can be overridden per row in CSV. Defaults to 'internet'."),
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

                # Be generous - accept 1 to 3 columns
                # Column 1: asset (IP or hostname) - required
                # Column 2: scan_level (optional)
                # Column 3: organization code (optional)
                for i, row in enumerate(rows, 1):
                    if not row or not row[0].strip():
                        continue  # Skip empty rows

                    col_count = len(row)
                    if col_count > 3:
                        raise ValidationError(
                            _(
                                "Row {row_num} has {col_count} columns. "
                                "Expected 1-3 columns (asset, scan_level, organization)."
                            ).format(row_num=i, col_count=col_count)
                        )

            except csv.Error as e:
                raise ValidationError(_("Error parsing CSV: {error}").format(error=str(e)))

        return cleaned_data
