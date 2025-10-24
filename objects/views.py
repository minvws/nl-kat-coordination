import csv
import io
import ipaddress
from typing import TYPE_CHECKING

import django_filters
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import DatabaseError
from django.db.models import OuterRef, Q, QuerySet, Subquery
from django.db.models.fields.json import KeyTextTransform
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView
from django_filters.views import FilterView
from djangoql.exceptions import DjangoQLParserError
from djangoql.queryset import apply_search

from objects.forms import (
    GenericAssetBulkCreateForm,
    GenericAssetCSVUploadForm,
    HostnameCSVUploadForm,
    IPAddressCSVUploadForm,
)
from objects.models import (
    DNSAAAARecord,
    DNSARecord,
    DNSCAARecord,
    DNSCNAMERecord,
    DNSMXRecord,
    DNSNSRecord,
    DNSPTRRecord,
    DNSSRVRecord,
    DNSTXTRecord,
    Finding,
    Hostname,
    IPAddress,
    IPPort,
    Network,
    ScanLevelEnum,
    Software,
)
from openkat.mixins import OrganizationFilterMixin
from openkat.models import Organization
from openkat.permissions import KATModelPermissionRequiredMixin
from plugins.models import Plugin
from tasks.models import ObjectSet, Task

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


class NetworkFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(label="Name", lookup_expr="icontains")
    object_set = django_filters.ModelChoiceFilter(
        label="Object Set", queryset=ObjectSet.objects.none(), empty_label="All objects", method="filter_by_object_set"
    )
    scan_level = django_filters.MultipleChoiceFilter(
        label="Scan level",
        choices=list(ScanLevelEnum.choices) + [("none", "No scan level")],
        method="filter_by_scan_level",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "scan-level-filter-checkboxes"}),
    )
    declared = django_filters.BooleanFilter(label="Declared")
    query = django_filters.CharFilter(label="Query", method="filter_by_query")

    class Meta:
        model = Network
        fields = ["name", "object_set", "declared", "query", "scan_level"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        network_ct = ContentType.objects.get_for_model(Network)
        queryset = ObjectSet.objects.filter(object_type=network_ct)
        if queryset.exists():
            self.filters["object_set"].queryset = queryset
        else:
            # Hide the filter if no object sets exist
            del self.filters["object_set"]

    def filter_by_object_set(self, queryset, name, value):
        # This method is called by django-filters, but we handle filtering in the view
        return queryset

    def filter_by_scan_level(self, queryset, name, value):
        if not value:
            return queryset

        q_objects = Q()

        for level in value:
            if level == "none":
                q_objects |= Q(scan_level__isnull=True)
            else:
                q_objects |= Q(scan_level=level)

        return queryset.filter(q_objects)

    def filter_by_query(self, queryset, name, value):
        if not value:
            return queryset

        try:
            return apply_search(queryset, value)
        except DjangoQLParserError:
            return queryset


class NetworkListView(OrganizationFilterMixin, FilterView):
    model = Network
    template_name = "objects/network_list.html"
    context_object_name = "networks"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = NetworkFilter
    ordering = ["-id"]
    http_method_names = ["get", "post"]

    def get_queryset(self) -> "QuerySet[Network]":
        queryset = super().get_queryset()

        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            object_set = ObjectSet.objects.get(id=object_set_id)
            queryset = object_set.get_query_objects()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:network_list"), "text": _("Networks")}]

        # Add warning if object set has manual objects that are being ignored
        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            object_set = ObjectSet.objects.get(id=object_set_id)
            if object_set.all_objects:
                messages.warning(
                    self.request,
                    _('"{}" has static objects that are ignored. Only the query is applied.').format(object_set.name),
                )

        # Add data for bulk actions
        network_ct = ContentType.objects.get_for_model(Network)
        context["object_sets"] = ObjectSet.objects.filter(object_type=network_ct)
        context["scan_levels"] = ScanLevelEnum
        context["plugins"] = Plugin.objects.filter(consumes__contains=["Network"])

        return context

    def post(self, request, *args, **kwargs):
        action_type = request.POST.get("action")
        selected_ids = request.POST.getlist("network")

        if not selected_ids:
            messages.warning(request, _("No networks selected."))
            return redirect(reverse("objects:network_list"))

        if action_type == "set-scan-level":
            scan_level = request.POST.get("scan-level")
            if scan_level == "none":
                # Remove scan level
                updated_count = Network.objects.filter(pk__in=selected_ids).update(scan_level=None, declared=False)
                messages.success(request, _("Removed scan level for {} networks.").format(updated_count))
            elif scan_level:
                # Set scan level
                updated_count = Network.objects.filter(pk__in=selected_ids).update(
                    scan_level=int(scan_level), declared=True
                )
                messages.success(request, _("Updated scan level for {} networks.").format(updated_count))
            else:
                messages.warning(request, _("No scan level selected."))
        elif action_type == "delete":
            try:
                Network.objects.filter(pk__in=selected_ids).delete()
                messages.success(request, _("Deleted {} networks.").format(len(selected_ids)))
            except DatabaseError:
                messages.warning(request, _("Failed to delete networks."))

        return redirect(reverse("objects:network_list"))


class NetworkDetailView(OrganizationFilterMixin, DetailView):
    model = Network
    template_name = "objects/network_detail.html"
    context_object_name = "network"

    object: Network

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build breadcrumb URL with organization parameters
        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:network_list")
        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("Networks")}]

        # Add findings for this network
        context["findings"] = Finding.objects.filter(object_type="network", object_id=self.object.pk)

        return context


class NetworkScanLevelDetailView(OrganizationFilterMixin, DetailView):
    model = Network
    template_name = "objects/network_detail_scan_level.html"
    context_object_name = "network"

    object: Network

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build breadcrumb URL with organization parameters
        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:network_list")
        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("Networks")}]

        # Add scan level form
        context["scan_level_form"] = ObjectScanLevelForm(instance=self.object)

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


class ObjectScanLevelForm(forms.Form):
    """Simple form for setting scan level directly on an object"""

    scan_level = forms.ChoiceField(
        choices=[("", "-")] + list(ScanLevelEnum.choices),
        required=False,
        label=_("Scan Level"),
        widget=forms.Select(attrs={"class": "scan-level-select"}),
    )
    declared = forms.BooleanField(required=False, label=_("Declared"), widget=forms.CheckboxInput())

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)

        if self.instance:
            self.fields["scan_level"].initial = self.instance.scan_level if self.instance.scan_level is not None else ""
            self.fields["declared"].initial = self.instance.declared


class HostnameScanLevelUpdateView(KATModelPermissionRequiredMixin, FormView):
    form_class = ObjectScanLevelForm

    def get_success_url(self):
        return reverse("objects:hostname_detail", kwargs={"pk": self.kwargs.get("pk")})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        hostname = Hostname.objects.get(pk=self.kwargs.get("pk"))
        kwargs["instance"] = hostname
        return kwargs

    def form_valid(self, form):
        hostname = Hostname.objects.get(pk=self.kwargs.get("pk"))
        scan_level_value = form.cleaned_data["scan_level"]
        declared = form.cleaned_data["declared"]

        # Update scan level
        if scan_level_value == "":
            hostname.scan_level = None
        else:
            hostname.scan_level = int(scan_level_value)
        hostname.declared = declared
        hostname.save()

        messages.success(self.request, _("Scan level updated successfully"))
        return super().form_valid(form)


class NetworkScanLevelUpdateView(KATModelPermissionRequiredMixin, FormView):
    form_class = ObjectScanLevelForm

    def get_success_url(self):
        return reverse("objects:network_detail", kwargs={"pk": self.kwargs.get("pk")})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        network = Network.objects.get(pk=self.kwargs.get("pk"))
        kwargs["instance"] = network
        return kwargs

    def form_valid(self, form):
        network = Network.objects.get(pk=self.kwargs.get("pk"))
        scan_level_value = form.cleaned_data["scan_level"]
        declared = form.cleaned_data["declared"]

        # Update scan level
        if scan_level_value == "":
            network.scan_level = None
        else:
            network.scan_level = int(scan_level_value)
        network.declared = declared
        network.save()

        messages.success(self.request, _("Scan level updated successfully"))
        return super().form_valid(form)


class FindingFilter(django_filters.FilterSet):
    finding_type__code = django_filters.CharFilter(label="Finding type", lookup_expr="icontains")
    object_search = django_filters.CharFilter(label="Object", method="filter_object_search")
    finding_type__score__gte = django_filters.NumberFilter(
        label="Minimum score", field_name="finding_type__score", lookup_expr="gte"
    )

    class Meta:
        model = Finding
        fields = ["finding_type__code", "object_search", "finding_type__score__gte"]

    def filter_object_search(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(object_human_readable__icontains=value)


class FindingListView(OrganizationFilterMixin, FilterView):
    model = Finding
    template_name = "objects/finding_list.html"
    context_object_name = "findings"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = FindingFilter
    ordering = ["-_valid_from"]

    def get_queryset(self) -> "QuerySet[Finding]":
        return super().get_queryset().prefetch_related("finding_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:finding_list"), "text": _("Findings")}]

        return context


class FindingCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Finding
    template_name = "objects/generic_object_form.html"
    fields = ["finding_type", "object_type", "object_id"]  # TODO: make easy
    success_url = reverse_lazy("objects:finding_list")


class FindingDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = Finding
    success_url = reverse_lazy("objects:finding_list")

    def form_invalid(self, form):
        return redirect(reverse("objects:finding_list"))


class IPAddressFilter(django_filters.FilterSet):
    address = django_filters.CharFilter(label="Address", lookup_expr="icontains")
    object_set = django_filters.ModelChoiceFilter(
        label="Object Set", queryset=ObjectSet.objects.none(), empty_label="All objects", method="filter_by_object_set"
    )
    scan_level = django_filters.MultipleChoiceFilter(
        label="Scan level",
        choices=list(ScanLevelEnum.choices) + [("none", "No scan level")],
        method="filter_by_scan_level",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "scan-level-filter-checkboxes"}),
    )
    declared = django_filters.BooleanFilter(label="Declared")
    query = django_filters.CharFilter(label="Query", method="filter_by_query")

    class Meta:
        model = IPAddress
        fields = ["address", "object_set", "declared", "query", "scan_level"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter object sets by IPAddress content type
        ipaddress_ct = ContentType.objects.get_for_model(IPAddress)
        queryset = ObjectSet.objects.filter(object_type=ipaddress_ct)
        if queryset.exists():
            self.filters["object_set"].queryset = queryset
        else:
            # Hide the filter if no object sets exist
            del self.filters["object_set"]

    def filter_by_object_set(self, queryset, name, value):
        # This method is called by django-filters, but we handle filtering in the view
        return queryset

    def filter_by_scan_level(self, queryset, name, value):
        if not value:
            return queryset

        q_objects = Q()

        for level in value:
            if level == "none":
                q_objects |= Q(scan_level__isnull=True)
            else:
                q_objects |= Q(scan_level=level)

        return queryset.filter(q_objects)

    def filter_by_query(self, queryset, name, value):
        if not value:
            return queryset

        try:
            return apply_search(queryset, value)
        except DjangoQLParserError:
            return queryset


class IPAddressListView(OrganizationFilterMixin, FilterView):
    model = IPAddress
    template_name = "objects/ipaddress_list.html"
    context_object_name = "ipaddresses"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = IPAddressFilter
    ordering = ["-id"]
    http_method_names = ["get", "post"]

    def get_queryset(self) -> "QuerySet[IPAddress]":
        queryset = super().get_queryset()

        # Apply object set filter if specified
        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            queryset = ObjectSet.objects.get(id=object_set_id).get_query_objects()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:ipaddress_list"), "text": _("IPAddresses")}]

        # Add warning if object set has manual objects that are being ignored
        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            obj_set = ObjectSet.objects.get(id=object_set_id)
            if obj_set.all_objects:
                messages.warning(
                    self.request,
                    _('"{}" has fixed objects that are ignored (only query results are shown).').format(obj_set.name),
                )

        # Add data for bulk actions
        ipaddress_ct = ContentType.objects.get_for_model(IPAddress)
        context["object_sets"] = ObjectSet.objects.filter(object_type=ipaddress_ct)
        context["scan_levels"] = ScanLevelEnum
        context["plugins"] = Plugin.objects.filter(consumes__contains=["IPAddress"])

        return context

    def post(self, request, *args, **kwargs):
        action_type = request.POST.get("action")
        selected_ids = request.POST.getlist("ipaddress")

        if not selected_ids:
            messages.warning(request, _("No IP addresses selected."))
            return redirect(reverse("objects:ipaddress_list"))

        if action_type == "scan":
            # Redirect to task creation page with selected IP addresses
            url = reverse("add_task") + "?" + "&".join([f"input_ips={selected}" for selected in selected_ids])
            return redirect(url)
        elif action_type == "create-object-set":
            # Redirect to object set creation with selected IP addresses
            ipaddress_ct = ContentType.objects.get_for_model(IPAddress)
            url = (
                reverse("add_object_set")
                + f"?object_type={ipaddress_ct.pk}&"
                + "&".join([f"objects={selected}" for selected in selected_ids])
            )
            return redirect(url)
        elif action_type == "set-scan-level":
            scan_level = request.POST.get("scan-level")
            if scan_level == "none":
                # Remove scan level
                updated_count = IPAddress.objects.filter(pk__in=selected_ids).update(scan_level=None, declared=False)
                messages.success(request, _("Removed scan level for {} IP addresses.").format(updated_count))
            elif scan_level:
                # Set scan level
                updated_count = IPAddress.objects.filter(pk__in=selected_ids).update(
                    scan_level=int(scan_level), declared=True
                )
                messages.success(request, _("Updated scan level for {} IP addresses.").format(updated_count))
            else:
                messages.warning(request, _("No scan level selected."))
        elif action_type == "delete":
            try:
                IPAddress.objects.filter(pk__in=selected_ids).delete()
                messages.success(request, _("Deleted {} IP addresses.").format(len(selected_ids)))
            except DatabaseError:
                messages.warning(request, _("Failed to delete IP addresses."))

        return redirect(reverse("objects:ipaddress_list"))


class IPAddressDetailView(OrganizationFilterMixin, DetailView):
    model = IPAddress
    template_name = "objects/ipaddress_detail.html"
    context_object_name = "ipaddress"

    object: IPAddress

    def get_queryset(self) -> "QuerySet[IPAddress]":
        return IPAddress.objects.prefetch_related("ipport_set")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build breadcrumb URL with organization parameters
        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:ipaddress_list")
        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("IPAddresses")}]

        # Add findings for this IP address
        context["findings"] = Finding.objects.filter(object_type="ipaddress", object_id=self.object.pk)

        # Add scan level form
        context["scan_level_form"] = ObjectScanLevelForm(instance=self.object)

        return context


class IPAddressScanLevelDetailView(OrganizationFilterMixin, DetailView):
    model = IPAddress
    template_name = "objects/ipaddress_detail_scan_level.html"
    context_object_name = "ipaddress"

    object: IPAddress

    def get_queryset(self) -> "QuerySet[IPAddress]":
        return IPAddress.objects.prefetch_related("ipport_set")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build breadcrumb URL with organization parameters
        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:ipaddress_list")
        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("IPAddresses")}]

        # Add scan level form
        context["scan_level_form"] = ObjectScanLevelForm(instance=self.object)

        return context


class IPAddressCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = IPAddress
    template_name = "objects/ipaddress_create.html"
    fields = ["network", "address"]
    success_url = reverse_lazy("objects:ipaddress_list")

    def get_initial(self):
        initial = super().get_initial()
        # Set default network to "internet" if it exists
        try:
            internet_network = Network.objects.get(name="internet")
            initial["network"] = internet_network
        except Network.DoesNotExist:
            pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["csv_form"] = IPAddressCSVUploadForm()
        context["csv_upload_url"] = reverse_lazy("objects:ipaddress_csv_upload")
        return context


class IPAddressCSVUploadView(KATModelPermissionRequiredMixin, FormView):
    template_name = "objects/ipaddress_csv_upload.html"
    form_class = IPAddressCSVUploadForm
    success_url = reverse_lazy("objects:ipaddress_list")
    permission_required = "openkat.add_ipaddress"

    def form_valid(self, form):
        network = form.cleaned_data.get("network")

        if not network:
            network, created = Network.objects.get_or_create(name="internet")

        csv_data = io.StringIO(form.cleaned_data["csv_file"].read().decode("UTF-8"))

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
    form_class = ObjectScanLevelForm

    def get_success_url(self):
        return reverse("objects:ipaddress_detail", kwargs={"pk": self.kwargs.get("pk")})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ipaddress = IPAddress.objects.get(pk=self.kwargs.get("pk"))
        kwargs["instance"] = ipaddress
        return kwargs

    def form_valid(self, form):
        ipaddress = IPAddress.objects.get(pk=self.kwargs.get("pk"))
        scan_level_value = form.cleaned_data["scan_level"]
        declared = form.cleaned_data["declared"]

        # Update scan level
        if scan_level_value == "":
            ipaddress.scan_level = None
        else:
            ipaddress.scan_level = int(scan_level_value)
        ipaddress.declared = declared
        ipaddress.save()

        messages.success(self.request, _("Scan level updated successfully"))
        return super().form_valid(form)


class HostnameFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(label="Name", lookup_expr="icontains")
    object_set = django_filters.ModelChoiceFilter(
        label="Object Set", queryset=ObjectSet.objects.none(), empty_label="All objects", method="filter_by_object_set"
    )
    scan_level = django_filters.MultipleChoiceFilter(
        label="Scan level",
        choices=list(ScanLevelEnum.choices) + [("none", "No scan level")],
        method="filter_by_scan_level",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "scan-level-filter-checkboxes"}),
    )
    declared = django_filters.BooleanFilter(label="Declared")
    query = django_filters.CharFilter(label="Query", method="filter_by_query")

    class Meta:
        model = Hostname
        fields = ["name", "object_set", "declared", "query", "scan_level"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter object sets by Hostname content type
        hostname_ct = ContentType.objects.get_for_model(Hostname)
        queryset = ObjectSet.objects.filter(object_type=hostname_ct)
        if queryset.exists():
            self.filters["object_set"].queryset = queryset
        else:
            # Hide the filter if no object sets exist
            del self.filters["object_set"]

    def filter_by_object_set(self, queryset, name, value):
        # This method is called by django-filters, but we handle filtering in the view
        return queryset

    def filter_by_scan_level(self, queryset, name, value):
        if not value:
            return queryset

        q_objects = Q()

        for level in value:
            if level == "none":
                q_objects |= Q(scan_level__isnull=True)
            else:
                q_objects |= Q(scan_level=level)

        return queryset.filter(q_objects)

    def filter_by_query(self, queryset, name, value):
        if not value:
            return queryset

        try:
            return apply_search(queryset, value)
        except DjangoQLParserError:
            return queryset


class HostnameListView(OrganizationFilterMixin, FilterView):
    model = Hostname
    template_name = "objects/hostname_list.html"
    context_object_name = "hostnames"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = HostnameFilter
    ordering = ["-id"]
    http_method_names = ["get", "post"]

    def get_queryset(self) -> "QuerySet[Hostname]":
        queryset = super().get_queryset()

        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            object_set = ObjectSet.objects.get(id=object_set_id)
            queryset = object_set.get_query_objects()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:hostname_list"), "text": _("Hostnames")}]

        # Add warning if object set has manual objects that are being ignored
        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            object_set = ObjectSet.objects.get(id=object_set_id)
            if object_set.all_objects:
                messages.warning(
                    self.request,
                    _('"{}" has static objects that are ignored. Only the query is applied.').format(object_set.name),
                )

        # Add data for bulk actions
        context["object_sets"] = ObjectSet.objects.filter(object_type=ContentType.objects.get_for_model(Hostname))
        context["scan_levels"] = ScanLevelEnum
        context["plugins"] = Plugin.objects.filter(consumes__contains=["Hostname"])

        return context

    def post(self, request, *args, **kwargs):
        action_type = request.POST.get("action")
        selected_ids = request.POST.getlist("hostname")

        if not selected_ids:
            messages.warning(request, _("No hostnames selected."))
            return redirect(reverse("objects:hostname_list"))

        if action_type == "scan":
            # Redirect to task creation page with selected hostnames
            url = reverse("add_task") + "?" + "&".join([f"input_hostnames={selected}" for selected in selected_ids])
            return redirect(url)
        elif action_type == "create-object-set":
            # Redirect to object set creation with selected hostnames
            hostname_ct = ContentType.objects.get_for_model(Hostname)
            url = (
                reverse("add_object_set")
                + f"?object_type={hostname_ct.pk}&"
                + "&".join([f"objects={selected}" for selected in selected_ids])
            )
            return redirect(url)
        elif action_type == "set-scan-level":
            scan_level = request.POST.get("scan-level")
            if scan_level == "none":
                # Remove scan level
                updated_count = Hostname.objects.filter(pk__in=selected_ids).update(scan_level=None, declared=False)
                messages.success(request, _("Removed scan level for {} hostnames.").format(updated_count))
            elif scan_level:
                # Set scan level
                updated_count = Hostname.objects.filter(pk__in=selected_ids).update(
                    scan_level=int(scan_level), declared=True
                )
                messages.success(request, _("Updated scan level for {} hostnames.").format(updated_count))
            else:
                messages.warning(request, _("No scan level selected."))
        elif action_type == "delete":
            try:
                Hostname.objects.filter(pk__in=selected_ids).delete()
                messages.success(request, _("Deleted {} hostnames.").format(len(selected_ids)))
            except DatabaseError:
                messages.warning(request, _("No plugin selected."))

        return redirect(reverse("objects:hostname_list"))


class HostnameDetailView(OrganizationFilterMixin, DetailView):
    model = Hostname
    template_name = "objects/hostname_detail.html"
    context_object_name = "hostname"

    object: Hostname

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build breadcrumb URL with organization parameters
        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:hostname_list")
        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("Hostnames")}]

        # Add DNS records to context
        context["dnsarecord_set"] = self.object.dnsarecord_set.all()
        context["dnsaaaarecord_set"] = self.object.dnsaaaarecord_set.all()
        context["dnscnamerecord_set"] = self.object.dnscnamerecord_set.all()
        context["dnsmxrecord_set"] = self.object.dnsmxrecord_set.all()
        context["dnsnsrecord_set"] = self.object.dnsnsrecord_set.all()
        context["dnsptrrecord_set"] = self.object.dnsptrrecord_set.all()
        context["dnscaarecord_set"] = self.object.dnscaarecord_set.all()
        context["dnstxtrecord_set"] = self.object.dnstxtrecord_set.all()
        context["dnssrvrecord_set"] = self.object.dnssrvrecord_set.all()

        # Reverse DNS records
        context["dnscnamerecord_target_set"] = self.object.dnscnamerecord_target_set.all()
        context["dnsmxrecord_mailserver"] = self.object.dnsmxrecord_mailserver.all()
        context["dnsnsrecord_nameserver"] = self.object.dnsnsrecord_nameserver.all()

        # Add findings for this hostname
        context["findings"] = Finding.objects.filter(object_type="hostname", object_id=self.object.pk)

        # Add scan level form
        context["scan_level_form"] = ObjectScanLevelForm(instance=self.object)

        return context


class HostnameScanLevelDetailView(OrganizationFilterMixin, DetailView):
    model = Hostname
    template_name = "objects/hostname_detail_scan_level.html"
    context_object_name = "hostname"

    object: Hostname

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build breadcrumb URL with organization parameters
        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:hostname_list")
        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("Hostnames")}]

        # Add scan level form
        context["scan_level_form"] = ObjectScanLevelForm(instance=self.object)

        return context


class HostnameTasksDetailView(OrganizationFilterMixin, ListView):
    model = Task
    template_name = "objects/hostname_detail_tasks.html"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    ordering = ["-created_at"]

    def get_queryset(self) -> "QuerySet[Task]":
        hostname = Hostname.objects.get(pk=self.kwargs.get("pk"))
        qs = Task.objects.filter(data__input_data__has_any_keys=[str(hostname.name)])
        qs = qs.annotate(
            plugin_name=Subquery(
                Plugin.objects.filter(plugin_id=KeyTextTransform("plugin_id", OuterRef("data"))).values("name")
            )
        )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hostname = Hostname.objects.get(pk=self.kwargs.get("pk"))
        context["hostname"] = hostname

        # Build breadcrumb URL with organization parameters
        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:hostname_list")

        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("Hostnames")}]

        return context


class IPAddressTasksDetailView(OrganizationFilterMixin, ListView):
    """Show tasks related to a specific IP address."""

    model = Task
    template_name = "objects/ipaddress_detail_tasks.html"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    ordering = ["-created_at"]

    def get_queryset(self) -> "QuerySet[Task]":
        ipaddress = IPAddress.objects.get(pk=self.kwargs.get("pk"))
        qs = Task.objects.filter(data__input_data__has_any_keys=[str(ipaddress.address)])
        qs = qs.annotate(
            plugin_name=Subquery(
                Plugin.objects.filter(plugin_id=KeyTextTransform("plugin_id", OuterRef("data"))).values("name")
            )
        )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ipaddress = IPAddress.objects.get(pk=self.kwargs.get("pk"))
        context["ipaddress"] = ipaddress

        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:ipaddress_list")
        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("IPAddresses")}]

        return context


class HostnameDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = Hostname
    success_url = reverse_lazy("objects:hostname_list")

    def form_invalid(self, form):
        return redirect(reverse("objects:hostname_list"))


class HostnameCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Hostname
    template_name = "objects/hostname_create.html"
    fields = ["network", "name"]
    success_url = reverse_lazy("objects:hostname_list")

    def get_initial(self):
        initial = super().get_initial()
        # Set default network to "internet" if it exists
        try:
            internet_network = Network.objects.get(name="internet")
            initial["network"] = internet_network
        except Network.DoesNotExist:
            pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["csv_form"] = HostnameCSVUploadForm()
        context["csv_upload_url"] = reverse_lazy("objects:hostname_csv_upload")
        return context


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
            network, created = Network.objects.get_or_create(name="internet")

        csv_data = io.StringIO(csv_file.read().decode("UTF-8"))

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
                messages.success(self.request, _("Successfully created {count} hostnames.").format(count=created_count))
            if skipped_count > 0:
                messages.info(
                    self.request, _("{count} hostnames already existed and were skipped.").format(count=skipped_count)
                )
            if error_count > 0:
                messages.warning(
                    self.request, _("{count} hostnames had errors and were not created.").format(count=error_count)
                )

        except csv.Error as e:
            messages.error(self.request, _("Error parsing CSV file: {error}").format(error=str(e)))

        return super().form_valid(form)


# DNS Record Delete Views
class DNSRecordDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    object: DNSARecord

    def get_success_url(self) -> str:
        return reverse("objects:hostname_detail", kwargs={"pk": self.object.hostname_id})


class DNSARecordDeleteView(DNSRecordDeleteView):
    model = DNSARecord


class DNSAAAARecordDeleteView(DNSRecordDeleteView):
    model = DNSAAAARecord


class DNSPTRRecordDeleteView(DNSRecordDeleteView):
    model = DNSPTRRecord


class DNSCNAMERecordDeleteView(DNSRecordDeleteView):
    model = DNSCNAMERecord


class DNSMXRecordDeleteView(DNSRecordDeleteView):
    model = DNSMXRecord


class DNSNSRecordDeleteView(DNSRecordDeleteView):
    model = DNSNSRecord


class DNSCAARecordDeleteView(DNSRecordDeleteView):
    model = DNSCAARecord


class DNSTXTRecordDeleteView(DNSRecordDeleteView):
    model = DNSTXTRecord


class DNSSRVRecordDeleteView(DNSRecordDeleteView):
    model = DNSSRVRecord


class IPPortDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = IPPort

    def get_success_url(self) -> str:
        return reverse("objects:ipaddress_detail", kwargs={"pk": self.object.address_id})


class IPPortSoftwareDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = Software
    http_method_names = ["post"]

    def form_valid(self, form):
        self.object = self.get_object()
        port_id = self.kwargs.get("port_pk")

        try:
            port = IPPort.objects.get(pk=port_id)
            port.software.remove(self.object)
            return redirect(self.get_success_url())
        except IPPort.DoesNotExist:
            return redirect(reverse("objects:ipaddress_list"))

    def get_success_url(self) -> str:
        port_id = self.kwargs.get("port_pk")
        try:
            port = IPPort.objects.get(pk=port_id)
            return reverse("objects:ipaddress_detail", kwargs={"pk": port.address_id})
        except IPPort.DoesNotExist:
            return reverse("objects:ipaddress_list")


def is_valid_ip(value: str) -> bool:
    """Check if a string is a valid IP address (IPv4 or IPv6)."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


class GenericAssetCreateView(KATModelPermissionRequiredMixin, FormView):
    """View for creating IP addresses and hostnames in bulk from textarea input."""

    template_name = "objects/generic_asset_create.html"
    form_class = GenericAssetBulkCreateForm
    success_url = reverse_lazy("objects:generic_asset_create")

    def get_permission_required(self):
        # Require both permissions since we create both types
        return ["openkat.add_ipaddress", "openkat.add_hostname"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["csv_form"] = GenericAssetCSVUploadForm()
        context["csv_upload_url"] = reverse_lazy("objects:generic_asset_csv_upload")
        return context

    def form_valid(self, form):
        assets = form.cleaned_data["assets"]
        network = form.cleaned_data.get("network")

        if not network:
            network, created = Network.objects.get_or_create(name="internet")

        ip_created = 0
        ip_skipped = 0
        hostname_created = 0
        hostname_skipped = 0
        error_count = 0

        for line_num, asset in enumerate(assets, 1):
            asset = asset.strip()
            if not asset:
                continue

            try:
                if is_valid_ip(asset):
                    # It's an IP address
                    ipaddress, created = IPAddress.objects.get_or_create(network=network, address=asset)
                    if created:
                        ip_created += 1
                    else:
                        ip_skipped += 1
                else:
                    # Treat as hostname
                    hostname, created = Hostname.objects.get_or_create(network=network, name=asset.lower())
                    if created:
                        hostname_created += 1
                    else:
                        hostname_skipped += 1
            except Exception as e:
                error_count += 1
                messages.warning(
                    self.request,
                    _("Error creating asset '{asset}' on line {line_num}: {error}").format(
                        asset=asset, line_num=line_num, error=str(e)
                    ),
                )

        # Success messages
        if ip_created > 0:
            messages.success(self.request, _("Successfully created {count} IP addresses.").format(count=ip_created))
        if hostname_created > 0:
            messages.success(self.request, _("Successfully created {count} hostnames.").format(count=hostname_created))

        # Info messages
        if ip_skipped > 0:
            messages.info(
                self.request, _("{count} IP addresses already existed and were skipped.").format(count=ip_skipped)
            )
        if hostname_skipped > 0:
            messages.info(
                self.request, _("{count} hostnames already existed and were skipped.").format(count=hostname_skipped)
            )

        # Error summary
        if error_count > 0:
            messages.warning(
                self.request, _("{count} assets had errors and were not created.").format(count=error_count)
            )

        return super().form_valid(form)


class GenericAssetCSVUploadView(KATModelPermissionRequiredMixin, FormView):
    """View for CSV upload of IP addresses and hostnames with optional scan level and organization."""

    template_name = "objects/generic_asset_csv_upload.html"
    form_class = GenericAssetCSVUploadForm
    success_url = reverse_lazy("objects:generic_asset_create")

    def get_permission_required(self):
        # Require both permissions since we create both types
        return ["openkat.add_ipaddress", "openkat.add_hostname"]

    def form_valid(self, form):
        csv_file = form.cleaned_data["csv_file"]
        default_network = form.cleaned_data.get("network")

        if not default_network:
            default_network, created = Network.objects.get_or_create(name="internet")

        csv_data = io.StringIO(csv_file.read().decode("UTF-8"))

        ip_created = 0
        ip_skipped = 0
        hostname_created = 0
        hostname_skipped = 0
        error_count = 0
        scan_levels_set = 0

        try:
            reader = csv.reader(csv_data, delimiter=",", quotechar='"')
            for row_num, row in enumerate(reader, 1):
                if not row or not row[0].strip():
                    continue  # Skip empty rows

                asset = row[0].strip()
                scan_level_value = None

                # Parse optional columns
                if len(row) >= 2 and row[1].strip():
                    try:
                        scan_level_value = int(row[1].strip())
                        if scan_level_value < 0 or scan_level_value > 4:
                            messages.warning(
                                self.request,
                                _(
                                    "Row {row_num}: Invalid scan level {level}. Must be 0-4. Skipping scan level."
                                ).format(row_num=row_num, level=scan_level_value),
                            )
                            scan_level_value = None
                    except ValueError:
                        messages.warning(
                            self.request,
                            _(
                                "Row {row_num}: Invalid scan level '{value}'. Must be an integer. Skipping scan level."
                            ).format(row_num=row_num, value=row[1].strip()),
                        )

                try:
                    # Determine if IP or hostname
                    if is_valid_ip(asset):
                        # Create IP address
                        ipaddress_obj, created = IPAddress.objects.get_or_create(network=default_network, address=asset)
                        if created:
                            ip_created += 1
                        else:
                            ip_skipped += 1

                        # Set scan level if provided
                        if scan_level_value is not None:
                            ipaddress_obj.scan_level = scan_level_value
                            ipaddress_obj.declared = True
                            ipaddress_obj.save()
                            scan_levels_set += 1

                    else:
                        # Create hostname
                        hostname_obj, created = Hostname.objects.get_or_create(
                            network=default_network, name=asset.lower()
                        )
                        if created:
                            hostname_created += 1
                        else:
                            hostname_skipped += 1

                        # Set scan level if provided
                        if scan_level_value is not None:
                            hostname_obj.scan_level = scan_level_value
                            hostname_obj.declared = True
                            hostname_obj.save()
                            scan_levels_set += 1

                except Exception as e:
                    error_count += 1
                    messages.warning(
                        self.request,
                        _("Error creating asset '{asset}' on row {row_num}: {error}").format(
                            asset=asset, row_num=row_num, error=str(e)
                        ),
                    )

            # Success messages
            if ip_created > 0:
                messages.success(self.request, _("Successfully created {count} IP addresses.").format(count=ip_created))
            if hostname_created > 0:
                messages.success(
                    self.request, _("Successfully created {count} hostnames.").format(count=hostname_created)
                )

            # Info messages
            if ip_skipped > 0:
                messages.info(
                    self.request, _("{count} IP addresses already existed and were skipped.").format(count=ip_skipped)
                )
            if hostname_skipped > 0:
                messages.info(
                    self.request,
                    _("{count} hostnames already existed and were skipped.").format(count=hostname_skipped),
                )

            if scan_levels_set > 0:
                messages.success(
                    self.request, _("Successfully set scan levels for {count} assets.").format(count=scan_levels_set)
                )

            # Error summary
            if error_count > 0:
                messages.warning(
                    self.request, _("{count} assets had errors and were not created.").format(count=error_count)
                )

        except csv.Error as e:
            messages.error(self.request, _("Error parsing CSV file: {error}").format(error=str(e)))

        return super().form_valid(form)

    def _get_organization(self, org_code: str | None) -> Organization | None:
        """Get organization by code, or return None if not found."""
        if not org_code:
            # If no org code provided, scan level cannot be set
            # This is expected - user can provide scan level in column 2 and org in column 3
            return None

        try:
            return Organization.objects.get(code=org_code)
        except Organization.DoesNotExist:
            messages.warning(
                self.request,
                _("Organization with code '{code}' not found. Skipping scan level for this row.").format(code=org_code),
            )
            return None
