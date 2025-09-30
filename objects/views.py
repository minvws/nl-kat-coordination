import csv
import io
from typing import TYPE_CHECKING

import django_filters
from django import forms
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Max, OuterRef, QuerySet, Subquery
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView
from django_filters.views import FilterView

from objects.forms import HostnameCSVUploadForm, IPAddressCSVUploadForm
from objects.models import Finding, Hostname, IPAddress, Network, ScanLevel, ScanLevelEnum
from openkat.models import Organization
from openkat.permissions import KATModelPermissionRequiredMixin

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


class NetworkFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(label="Name", lookup_expr="contains")

    class Meta:
        model = Network
        fields = ["name"]


class NetworkListView(FilterView):
    model = Network
    template_name = "objects/network_list.html"
    context_object_name = "networks"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = NetworkFilter

    def get_queryset(self) -> "QuerySet[Network]":
        scan_level_subquery = (
            ScanLevel.objects.filter(object_type="network", object_id=OuterRef("id"))
            .values("object_id")
            .order_by()
            .annotate(max_scan_level=Max("scan_level"))  # collect scan levels in subquery
        )

        return Network.objects.annotate(max_scan_level=Subquery(scan_level_subquery.values("max_scan_level")))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:network_list"), "text": _("Networks")}]

        return context


class NetworkDetailView(DetailView):
    model = Network
    template_name = "objects/network_detail.html"
    context_object_name = "network"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:network_list"), "text": _("Networks")}]
        context["scan_levels"] = ScanLevel.objects.filter(object_id=self.object.id)

        return context


class NetworkCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Network
    template_name = "objects/generic_object_form.html"
    fields = ["name"]
    success_url = reverse_lazy("objects:network_list")


class NetworkDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = Network
    success_url = reverse_lazy("objects:network_list")

    def form_invalid(self, form):
        return redirect(reverse("objects:network_list"))


class ScanLevelUpdateForm(forms.ModelForm):
    """Form for updating scan level of an object."""

    scan_level = forms.ChoiceField(
        choices=ScanLevelEnum.choices,
        required=True,
        label=_("Scan Level"),
        widget=forms.Select(attrs={"class": "scan-level-select"}),
    )

    class Meta:
        model = ScanLevel
        fields = ["scan_level"]

    def __init__(self, *args, **kwargs):
        self.object_id = kwargs.pop("object_id", None)
        self.object_type = kwargs.pop("object_type", None)
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.declared = True
        instance.object_id = self.object_id
        instance.object_type = self.object_type
        instance.organization = self.organization

        if commit:
            instance.save()
        return instance


class HostnameScanLevelUpdateView(KATModelPermissionRequiredMixin, FormView):
    form_class = ScanLevelUpdateForm

    def get_success_url(self):
        return reverse("objects:hostname_detail", kwargs={"pk": self.kwargs.get("pk")})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        hostname_id = self.kwargs.get("pk")
        organization_id = self.kwargs.get("organization_id")

        kwargs["object_id"] = hostname_id
        kwargs["object_type"] = "hostname"
        kwargs["organization"] = Organization.objects.get(id=organization_id)

        # Try to get existing scan level
        try:
            scan_level = ScanLevel.objects.get(
                object_id=hostname_id, object_type="hostname", organization_id=organization_id
            )
            kwargs["instance"] = scan_level
        except ScanLevel.DoesNotExist:
            pass

        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class NetworkScanLevelUpdateView(KATModelPermissionRequiredMixin, FormView):
    form_class = ScanLevelUpdateForm

    def get_success_url(self):
        return reverse("objects:network_detail", kwargs={"pk": self.kwargs.get("pk")})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        network_id = self.kwargs.get("pk")
        organization_id = self.kwargs.get("organization_id")

        kwargs["object_id"] = network_id
        kwargs["object_type"] = "network"
        kwargs["organization"] = Organization.objects.get(id=organization_id)

        # Try to get existing scan level
        try:
            scan_level = ScanLevel.objects.get(
                object_id=network_id, object_type="network", organization_id=organization_id
            )
            kwargs["instance"] = scan_level
        except ScanLevel.DoesNotExist:
            pass

        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class FindingFilter(django_filters.FilterSet):
    finding_type__code = django_filters.CharFilter(label="Finding Type", lookup_expr="contains")

    class Meta:
        model = Finding
        fields = ["finding_type__code"]


class FindingListView(FilterView):
    model = Finding
    template_name = "objects/finding_list.html"
    context_object_name = "findings"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = FindingFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:finding_list"), "text": _("Findings")}]

        return context


class FindingCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Finding
    template_name = "objects/generic_object_form.html"
    fields = ["organization", "finding_type", "object_type", "object_id"]  # TODO: make easy
    success_url = reverse_lazy("objects:finding_list")


class FindingDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = Finding
    success_url = reverse_lazy("objects:finding_list")

    def form_invalid(self, form):
        return redirect(reverse("objects:finding_list"))


class IPAddressFilter(django_filters.FilterSet):
    address = django_filters.CharFilter(label="Address", lookup_expr="contains")

    class Meta:
        model = IPAddress
        fields = ["address"]


class IPAddressListView(FilterView):
    model = IPAddress
    template_name = "objects/ipaddress_list.html"
    context_object_name = "ipaddresses"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = IPAddressFilter

    def get_queryset(self) -> "QuerySet[IPAddress]":
        scan_level_subquery = (
            ScanLevel.objects.filter(object_type="ipaddress", object_id=OuterRef("id"))
            .values("object_id")
            .order_by()
            .annotate(max_scan_level=Max("scan_level"))  # collect scan levels in subquery
        )

        return IPAddress.objects.select_related("network").annotate(
            max_scan_level=Subquery(scan_level_subquery.values("max_scan_level"))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:ipaddress_list"), "text": _("IPAddresses")}]

        return context


class IPAddressDetailView(DetailView):
    model = IPAddress
    template_name = "objects/ipaddress_detail.html"
    context_object_name = "ipaddress"

    def get_queryset(self) -> "QuerySet[IPAddress]":
        return IPAddress.objects.select_related("network").prefetch_related("ipport_set")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:ipaddress_list"), "text": _("IPAddresses")}]
        context["scan_levels"] = ScanLevel.objects.filter(object_id=self.object.id)

        return context


class IPAddressCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = IPAddress
    template_name = "objects/generic_object_form.html"
    fields = ["network", "address"]
    success_url = reverse_lazy("objects:ipaddress_list")


class IPAddressCSVUploadView(KATModelPermissionRequiredMixin, FormView):
    template_name = "objects/ipaddress_csv_upload.html"
    form_class = IPAddressCSVUploadForm
    success_url = reverse_lazy("objects:ipaddress_list")
    permission_required = "openkat.add_ipaddress"

    def form_valid(self, form):
        csv_file = form.cleaned_data["csv_file"]
        network = form.cleaned_data.get("network")

        # Default to "internet" network if not specified
        if not network:
            network, _ = Network.objects.get_or_create(name="internet")

        csv_raw_data = csv_file.read()
        csv_data = io.StringIO(csv_raw_data.decode("UTF-8"))

        created_count = 0
        error_count = 0
        skipped_count = 0

        try:
            reader = csv.reader(csv_data, delimiter=",", quotechar='"')
            for row_num, row in enumerate(reader, 1):
                if not row or not row[0].strip():
                    continue  # Skip empty rows

                address = row[0].strip()

                try:
                    with transaction.atomic():
                        ipaddress, created = IPAddress.objects.get_or_create(network=network, address=address)
                        if created:
                            created_count += 1
                        else:
                            skipped_count += 1
                except Exception as e:
                    error_count += 1
                    messages.add_message(
                        self.request,
                        messages.WARNING,
                        _("Error creating IP address '{address}' on row {row_num}: {error}").format(
                            address=address, row_num=row_num, error=str(e)
                        ),
                    )

            if created_count > 0:
                messages.add_message(
                    self.request,
                    messages.SUCCESS,
                    _("Successfully created {count} IP addresses.").format(count=created_count),
                )
            if skipped_count > 0:
                messages.add_message(
                    self.request,
                    messages.INFO,
                    _("{count} IP addresses already existed and were skipped.").format(count=skipped_count),
                )
            if error_count > 0:
                messages.add_message(
                    self.request,
                    messages.WARNING,
                    _("{count} IP addresses had errors and were not created.").format(count=error_count),
                )

        except csv.Error as e:
            messages.add_message(
                self.request, messages.ERROR, _("Error parsing CSV file: {error}").format(error=str(e))
            )

        return super().form_valid(form)


class IPAddressDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = IPAddress
    success_url = reverse_lazy("objects:ipaddress_list")

    def form_invalid(self, form):
        return redirect(reverse("objects:ipaddress_list"))


class IPAddressScanLevelUpdateView(KATModelPermissionRequiredMixin, FormView):
    form_class = ScanLevelUpdateForm

    def get_success_url(self):
        return reverse("objects:ipaddress_detail", kwargs={"pk": self.kwargs.get("pk")})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ipaddress_id = self.kwargs.get("pk")
        organization_id = self.kwargs.get("organization_id")

        kwargs["object_id"] = ipaddress_id
        kwargs["object_type"] = "ipaddress"
        kwargs["organization"] = Organization.objects.get(id=organization_id)

        # Try to get existing scan level
        try:
            scan_level = ScanLevel.objects.get(
                object_id=ipaddress_id, object_type="ipaddress", organization_id=organization_id
            )
            kwargs["instance"] = scan_level
        except ScanLevel.DoesNotExist:
            pass

        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class HostnameFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(label="Name", lookup_expr="contains")

    class Meta:
        model = Hostname
        fields = ["name"]


class HostnameListView(FilterView):
    model = Hostname
    template_name = "objects/hostname_list.html"
    context_object_name = "hostnames"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = HostnameFilter

    def get_queryset(self) -> "QuerySet[Hostname]":
        scan_level_subquery = (
            ScanLevel.objects.filter(object_type="hostname", object_id=OuterRef("id"))
            .values("object_id")
            .order_by()
            .annotate(max_scan_level=Max("scan_level"))  # collect scan levels in subquery
        )

        return Hostname.objects.select_related("network").annotate(
            max_scan_level=Subquery(scan_level_subquery.values("max_scan_level"))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:hostname_list"), "text": _("Hostnames")}]

        return context


class HostnameDetailView(DetailView):
    model = Hostname
    template_name = "objects/hostname_detail.html"
    context_object_name = "hostname"

    def get_queryset(self) -> "QuerySet[Hostname]":
        return Hostname.objects.select_related("network").prefetch_related(
            "dnsarecord_set",
            "dnsaaaarecord_set",
            "dnsptrrecord_set",
            "cname_records",
            "cname_targets",
            "mx_records",
            "mx_targets",
            "ns_records",
            "ns_targets",
            "dnscaarecord_set",
            "dnstxtrecord_set",
            "dnssrvrecord_set",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:hostname_list"), "text": _("Hostnames")}]
        context["scan_levels"] = ScanLevel.objects.filter(object_id=self.object.id)

        return context


class HostnameDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = Hostname
    success_url = reverse_lazy("objects:hostname_list")

    def form_invalid(self, form):
        return redirect(reverse("objects:hostname_list"))


class HostnameCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Hostname
    template_name = "objects/generic_object_form.html"
    fields = ["network", "name"]
    success_url = reverse_lazy("objects:hostname_list")


class HostnameCSVUploadView(KATModelPermissionRequiredMixin, FormView):
    template_name = "objects/hostname_csv_upload.html"
    form_class = HostnameCSVUploadForm
    success_url = reverse_lazy("objects:hostname_list")
    permission_required = "openkat.add_hostname"

    def form_valid(self, form):
        csv_file = form.cleaned_data["csv_file"]
        network = form.cleaned_data.get("network")

        # Default to "internet" network if not specified
        if not network:
            network, _ = Network.objects.get_or_create(name="internet")

        csv_raw_data = csv_file.read()
        csv_data = io.StringIO(csv_raw_data.decode("UTF-8"))

        created_count = 0
        error_count = 0
        skipped_count = 0

        try:
            reader = csv.reader(csv_data, delimiter=",", quotechar='"')
            for row_num, row in enumerate(reader, 1):
                if not row or not row[0].strip():
                    continue  # Skip empty rows

                name = row[0].strip()

                try:
                    with transaction.atomic():
                        hostname, created = Hostname.objects.get_or_create(network=network, name=name)
                        if created:
                            created_count += 1
                        else:
                            skipped_count += 1
                except Exception as e:
                    error_count += 1
                    messages.add_message(
                        self.request,
                        messages.WARNING,
                        _("Error creating hostname '{name}' on row {row_num}: {error}").format(
                            name=name, row_num=row_num, error=str(e)
                        ),
                    )

            if created_count > 0:
                messages.add_message(
                    self.request,
                    messages.SUCCESS,
                    _("Successfully created {count} hostnames.").format(count=created_count),
                )
            if skipped_count > 0:
                messages.add_message(
                    self.request,
                    messages.INFO,
                    _("{count} hostnames already existed and were skipped.").format(count=skipped_count),
                )
            if error_count > 0:
                messages.add_message(
                    self.request,
                    messages.WARNING,
                    _("{count} hostnames had errors and were not created.").format(count=error_count),
                )

        except csv.Error as e:
            messages.add_message(
                self.request, messages.ERROR, _("Error parsing CSV file: {error}").format(error=str(e))
            )

        return super().form_valid(form)
