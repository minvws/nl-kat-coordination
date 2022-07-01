import csv
import io
from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django_otp.decorators import otp_required
from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network, IPAddressV4, IPAddressV6

from rocky.settings import OCTOPOES_API
from tools.models import Organization
from tools.user_helpers import is_red_team


def _save_ooi(ooi, organization) -> None:
    connector = OctopoesAPIConnector(OCTOPOES_API, organization)
    connector.save_declaration(
        Declaration(ooi=ooi, valid_time=datetime.now(timezone.utc))
    )


def proccess_csv(request, io_string, context):
    internet = Network(name="internet")
    hostnames_and_organizations = []
    codes = list(Organization.objects.all().values_list("code", flat=True))

    try:
        for row in csv.reader(io_string, delimiter=",", quotechar='"'):
            if row[1] not in codes:
                messages.error(
                    request,
                    _("Organization code not in database"),
                )
                return render(request, "hostname_and_ip_upload.html", context)

            if row and row[0] != "":
                # append a tuple with hostname object and org
                if row[2] == "Hostname":
                    hostnames_and_organizations.append(
                        (Hostname(name=row[0], network=internet.reference), row[1])
                    )
                elif row[2] == "IPAddressV4":
                    hostnames_and_organizations.append(
                        (
                            IPAddressV4(address=row[0], network=internet.reference),
                            row[1],
                        )
                    )
                elif row[2] == "IPAddressV6":
                    hostnames_and_organizations.append(
                        (
                            IPAddressV6(address=row[0], network=internet.reference),
                            row[1],
                        )
                    )
                else:
                    messages.error(
                        request,
                        _(
                            "Only Hostname, IPAddressV4 and IPAddressV6 are currently supported as upload OOIs"
                        ),
                    )
                    return render(request, "hostname_and_ip_upload.html", context)
    except (csv.Error, IndexError) as e:
        messages.error(
            request,
            f"{_('An error has occurred during the parsing of the csv file:')} {e}",
        )
        return render(request, "hostname_and_ip_upload.html", context)

    for hostname, organization in hostnames_and_organizations:
        _save_ooi(hostname, organization)

    return HttpResponseRedirect(reverse("ooi_list"))


@user_passes_test(is_red_team)
@otp_required
@require_http_methods(["GET", "POST"])
def upload(request):

    context = {"breadcrumbs": [{"url": reverse("upload"), "text": _("Upload CSV")}]}
    if request.method == "GET":
        return render(request, "hostname_and_ip_upload.html", context)

    if request.method == "POST":
        csv_file = request.FILES["hostname_and_ip_file"]

        if not csv_file.name.endswith(".csv"):
            messages.error(request, _("Only csv supported"))
            return render(request, "hostname_and_ip_upload.html", context)

        try:
            data_set = csv_file.read().decode("UTF-8")
        except UnicodeDecodeError:
            messages.error(request, _("File could not be decoded"))
            return render(request, "hostname_and_ip_upload.html", context)
        if not data_set:
            messages.error(request, _("The uploaded file is empty."))
            return render(request, "hostname_and_ip_upload.html", context)
        else:
            io_string = io.StringIO(data_set)
            # remove titles
            next(io_string)
            return proccess_csv(request, io_string, context)
