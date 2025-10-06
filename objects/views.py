import csv
import io
from typing import TYPE_CHECKING, Any

import django_filters
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Max, OuterRef, Q, QuerySet, Subquery
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView
from django_filters.views import FilterView

from objects.forms import HostnameCSVUploadForm, IPAddressCSVUploadForm
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
    Network,
    ScanLevel,
    ScanLevelEnum,
)
from openkat.mixins import OrganizationFilterMixin
from openkat.models import Organization
from openkat.permissions import KATModelPermissionRequiredMixin
from tasks.models import ObjectSet

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

    class Meta:
        model = Network
        fields = ["name", "object_set", "scan_level"]

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
                q_objects |= Q(max_scan_level__isnull=True)
            else:
                q_objects |= Q(max_scan_level=level)

        return queryset.filter(q_objects)


class NetworkListView(OrganizationFilterMixin, FilterView):
    model = Network
    template_name = "objects/network_list.html"
    context_object_name = "networks"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = NetworkFilter

    def get_queryset(self) -> "QuerySet[Network]":
        organization_codes = self.request.GET.getlist("organization")
        scan_level_filter: dict[str, Any] = {"object_type": "network", "object_id": OuterRef("id")}

        if organization_codes:
            scan_level_filter["organization__in"] = list(
                Organization.objects.filter(code__in=organization_codes).values_list("id", flat=True)
            )

        scan_level_subquery = (
            ScanLevel.objects.filter(**scan_level_filter)
            .values("object_id")
            .order_by()
            .annotate(max_scan_level=Max("scan_level"))  # collect scan levels in subquery
        )

        queryset = Network.objects.annotate(max_scan_level=Subquery(scan_level_subquery.values("max_scan_level")))

        # Apply object set filter if specified
        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            try:
                object_set = ObjectSet.objects.get(id=object_set_id)
                queryset = object_set.get_query_objects()
                # Re-apply scan level annotation to the filtered queryset
                queryset = queryset.annotate(max_scan_level=Subquery(scan_level_subquery.values("max_scan_level")))
            except ObjectSet.DoesNotExist:
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:network_list"), "text": _("Networks")}]

        # Add warning if object set has manual objects that are being ignored
        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            try:
                object_set = ObjectSet.objects.get(id=object_set_id)
                if object_set.all_objects:
                    messages.warning(
                        self.request,
                        _('"{}" has manually added objects that are ignored. Only the query is applied.').format(
                            object_set.name
                        ),
                    )
            except ObjectSet.DoesNotExist:
                pass

        return context


class NetworkDetailView(OrganizationFilterMixin, DetailView):
    model = Network
    template_name = "objects/network_detail.html"
    context_object_name = "network"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build breadcrumb URL with organization parameters
        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:network_list")
        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("Networks")}]

        # Filter scan levels by selected organization only if exactly one is selected
        scan_levels = ScanLevel.objects.filter(object_id=self.object.id, object_type="network")
        if organization_codes:
            scan_levels = scan_levels.filter(
                organization__in=list(
                    Organization.objects.filter(code__in=organization_codes).values_list("id", flat=True)
                )
            )

        context["scan_levels"] = scan_levels
        context["scan_level_form"] = ScanLevelAddForm

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


class ScanLevelAddForm(forms.ModelForm):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        required=True,
        label=_("Organization"),
        widget=forms.Select(attrs={"class": "organization-select"}),
    )
    scan_level = forms.ChoiceField(
        choices=ScanLevelEnum.choices,
        required=True,
        label=_("Scan Level"),
        widget=forms.Select(attrs={"class": "scan-level-select"}),
    )

    class Meta:
        model = ScanLevel
        fields = ["organization", "scan_level"]

    def __init__(self, *args, **kwargs):
        self.object_id = kwargs.pop("object_id", None)
        self.object_type = kwargs.pop("object_type", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.declared = True
        instance.object_id = self.object_id
        instance.object_type = self.object_type

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


class HostnameScanLevelAddView(KATModelPermissionRequiredMixin, FormView):
    form_class = ScanLevelAddForm

    def get_success_url(self):
        return reverse("objects:hostname_detail", kwargs={"pk": self.kwargs.get("pk")})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        hostname_id = self.kwargs.get("pk")

        kwargs["object_id"] = hostname_id
        kwargs["object_type"] = "hostname"

        return kwargs

    def form_valid(self, form):
        hostname_id = self.kwargs.get("pk")
        organization = form.cleaned_data["organization"]
        scan_level_value = form.cleaned_data["scan_level"]

        # Use get_or_create to avoid duplicates
        scan_level, created = ScanLevel.objects.get_or_create(
            object_id=hostname_id,
            object_type="hostname",
            organization=organization,
            defaults={"scan_level": scan_level_value, "declared": True},
        )

        # If it already existed, update the scan level
        if not created:
            scan_level.scan_level = scan_level_value
            scan_level.declared = True
            scan_level.save()

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


class NetworkScanLevelAddView(KATModelPermissionRequiredMixin, FormView):
    form_class = ScanLevelAddForm

    def get_success_url(self):
        return reverse("objects:network_detail", kwargs={"pk": self.kwargs.get("pk")})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["object_id"] = self.kwargs.get("pk")
        kwargs["object_type"] = "network"

        return kwargs

    def form_valid(self, form):
        scan_level_value = form.cleaned_data["scan_level"]

        # Use get_or_create to avoid duplicates
        scan_level, created = ScanLevel.objects.get_or_create(
            object_id=self.kwargs.get("pk"),
            object_type="network",
            organization=form.cleaned_data["organization"],
            defaults={"scan_level": scan_level_value, "declared": True},
        )

        # If it already existed, update the scan level
        if not created:
            scan_level.scan_level = scan_level_value
            scan_level.declared = True
            scan_level.save()

        return super().form_valid(form)


class FindingFilter(django_filters.FilterSet):
    finding_type__code = django_filters.CharFilter(label="Finding Type", lookup_expr="icontains")

    class Meta:
        model = Finding
        fields = ["finding_type__code"]


class FindingListView(OrganizationFilterMixin, FilterView):
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

    class Meta:
        model = IPAddress
        fields = ["address", "object_set", "scan_level"]

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
                q_objects |= Q(max_scan_level__isnull=True)
            else:
                q_objects |= Q(max_scan_level=level)

        return queryset.filter(q_objects)


class IPAddressListView(OrganizationFilterMixin, FilterView):
    model = IPAddress
    template_name = "objects/ipaddress_list.html"
    context_object_name = "ipaddresses"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = IPAddressFilter

    def get_queryset(self) -> "QuerySet[IPAddress]":
        organization_codes = self.request.GET.getlist("organization")
        scan_level_filter: dict[str, Any] = {"object_type": "ipaddress", "object_id": OuterRef("id")}

        if organization_codes:
            scan_level_filter["organization__in"] = list(
                Organization.objects.filter(code__in=organization_codes).values_list("id", flat=True)
            )

        scan_level_subquery = (
            ScanLevel.objects.filter(**scan_level_filter)
            .values("object_id")
            .order_by()
            .annotate(max_scan_level=Max("scan_level"))  # collect scan levels in subquery
        )

        queryset = IPAddress.objects.annotate(max_scan_level=Subquery(scan_level_subquery.values("max_scan_level")))
        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            try:
                queryset = ObjectSet.objects.get(id=object_set_id).get_query_objects()
                # Re-apply scan level annotation to the filtered queryset
                queryset = queryset.annotate(max_scan_level=Subquery(scan_level_subquery.values("max_scan_level")))
            except ObjectSet.DoesNotExist:
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:ipaddress_list"), "text": _("IPAddresses")}]

        # Add warning if object set has manual objects that are being ignored
        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            try:
                obj_set = ObjectSet.objects.get(id=object_set_id)
                if obj_set.all_objects:
                    messages.warning(
                        self.request,
                        _('"{}" has fixed objects that are ignored (only query results are shown).').format(
                            obj_set.name
                        ),
                    )
            except ObjectSet.DoesNotExist:
                pass

        return context


class IPAddressDetailView(OrganizationFilterMixin, DetailView):
    model = IPAddress
    template_name = "objects/ipaddress_detail.html"
    context_object_name = "ipaddress"

    def get_queryset(self) -> "QuerySet[IPAddress]":
        return IPAddress.objects.select_related("network").prefetch_related("ipport_set")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build breadcrumb URL with organization parameters
        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:ipaddress_list")
        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("IPAddresses")}]

        # Filter scan levels by selected organization only if exactly one is selected
        scan_levels = ScanLevel.objects.filter(object_id=self.object.id, object_type="ipaddress")
        if organization_codes:
            scan_levels = scan_levels.filter(
                organization__in=list(
                    Organization.objects.filter(code__in=organization_codes).values_list("id", flat=True)
                )
            )

        context["scan_levels"] = scan_levels
        context["scan_level_form"] = ScanLevelAddForm

        return context


class IPAddressCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = IPAddress
    template_name = "objects/ipaddress_create.html"
    fields = ["network", "address"]
    success_url = reverse_lazy("objects:ipaddress_list")

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


class IPAddressScanLevelAddView(KATModelPermissionRequiredMixin, FormView):
    form_class = ScanLevelAddForm

    def get_success_url(self):
        return reverse("objects:ipaddress_detail", kwargs={"pk": self.kwargs.get("pk")})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ipaddress_id = self.kwargs.get("pk")

        kwargs["object_id"] = ipaddress_id
        kwargs["object_type"] = "ipaddress"

        return kwargs

    def form_valid(self, form):
        ipaddress_id = self.kwargs.get("pk")
        organization = form.cleaned_data["organization"]
        scan_level_value = form.cleaned_data["scan_level"]

        # Use get_or_create to avoid duplicates
        scan_level, created = ScanLevel.objects.get_or_create(
            object_id=ipaddress_id,
            object_type="ipaddress",
            organization=organization,
            defaults={"scan_level": scan_level_value, "declared": True},
        )

        # If it already existed, update the scan level
        if not created:
            scan_level.scan_level = scan_level_value
            scan_level.declared = True
            scan_level.save()

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

    class Meta:
        model = Hostname
        fields = ["name", "object_set", "scan_level"]

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
                q_objects |= Q(max_scan_level__isnull=True)
            else:
                q_objects |= Q(max_scan_level=level)

        return queryset.filter(q_objects)


class HostnameListView(OrganizationFilterMixin, FilterView):
    model = Hostname
    template_name = "objects/hostname_list.html"
    context_object_name = "hostnames"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = HostnameFilter

    def get_queryset(self) -> "QuerySet[Hostname]":
        organization_codes = self.request.GET.getlist("organization")
        scan_level_filter: dict[str, Any] = {"object_type": "hostname", "object_id": OuterRef("id")}

        if organization_codes:
            scan_level_filter["organization__in"] = list(
                Organization.objects.filter(code__in=organization_codes).values_list("id", flat=True)
            )

        scan_level_subquery = (
            ScanLevel.objects.filter(**scan_level_filter)
            .values("object_id")
            .order_by()
            .annotate(max_scan_level=Max("scan_level"))  # collect scan levels in subquery
        )

        queryset = Hostname.objects.select_related("network").annotate(
            max_scan_level=Subquery(scan_level_subquery.values("max_scan_level"))
        )

        # Apply object set filter if specified
        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            try:
                object_set = ObjectSet.objects.get(id=object_set_id)
                queryset = object_set.get_query_objects().select_related("network")
                # Re-apply scan level annotation to the filtered queryset
                queryset = queryset.annotate(max_scan_level=Subquery(scan_level_subquery.values("max_scan_level")))
            except ObjectSet.DoesNotExist:
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:hostname_list"), "text": _("Hostnames")}]

        # Add warning if object set has manual objects that are being ignored
        object_set_id = self.request.GET.get("object_set")
        if object_set_id:
            try:
                object_set = ObjectSet.objects.get(id=object_set_id)
                if object_set.all_objects:
                    messages.warning(
                        self.request,
                        _('"{}" has manually added objects that are ignored. Only the query is applied.').format(
                            object_set.name
                        ),
                    )
            except ObjectSet.DoesNotExist:
                pass

        return context


class HostnameDetailView(OrganizationFilterMixin, DetailView):
    model = Hostname
    template_name = "objects/hostname_detail.html"
    context_object_name = "hostname"

    def get_queryset(self) -> "QuerySet[Hostname]":
        return Hostname.objects.select_related("network")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build breadcrumb URL with organization parameters
        organization_codes = self.request.GET.getlist("organization")
        breadcrumb_url = reverse("objects:hostname_list")
        if organization_codes:
            breadcrumb_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        context["breadcrumbs"] = [{"url": breadcrumb_url, "text": _("Hostnames")}]

        # Filter scan levels by selected organization only if exactly one is selected
        scan_levels = ScanLevel.objects.filter(object_id=self.object.id, object_type="hostname")

        if organization_codes:
            scan_levels = scan_levels.filter(
                organization__in=list(
                    Organization.objects.filter(code__in=organization_codes).values_list("id", flat=True)
                )
            )
        context["scan_levels"] = scan_levels
        context["scan_level_form"] = ScanLevelAddForm

        # Add max scan level annotations for DNS records
        organization_ids = None
        if organization_codes:
            organization_ids = list(
                Organization.objects.filter(code__in=organization_codes).values_list("id", flat=True)
            )

        def dns_record_scan_level_subquery(object_type: str) -> Subquery:
            scan_level_filter: dict[str, Any] = {"object_type": object_type, "object_id": OuterRef("id")}
            if organization_ids:
                scan_level_filter["organization__in"] = organization_ids

            return Subquery(
                ScanLevel.objects.filter(**scan_level_filter)
                .values("object_id")
                .order_by()
                .annotate(max_scan_level=Max("scan_level"))
                .values("max_scan_level")
            )

        # Annotate DNS records with their own max scan levels
        context["dnsarecord_set"] = self.object.dnsarecord_set.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnsarecord")
        )
        context["dnsaaaarecord_set"] = self.object.dnsaaaarecord_set.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnsaaaarecord")
        )
        context["dnscnamerecord_set"] = self.object.dnscnamerecord_set.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnscnamerecord")
        )
        context["dnsmxrecord_set"] = self.object.dnsmxrecord_set.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnsmxrecord")
        )
        context["dnsnsrecord_set"] = self.object.dnsnsrecord_set.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnsnsrecord")
        )
        context["dnsptrrecord_set"] = self.object.dnsptrrecord_set.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnsptrrecord")
        )
        context["dnscaarecord_set"] = self.object.dnscaarecord_set.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnscaarecord")
        )
        context["dnstxtrecord_set"] = self.object.dnstxtrecord_set.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnstxtrecord")
        )
        context["dnssrvrecord_set"] = self.object.dnssrvrecord_set.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnssrvrecord")
        )

        # Reverse DNS records
        context["dnscnamerecord_target_set"] = self.object.dnscnamerecord_target_set.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnscnamerecord")
        )
        context["dnsmxrecord_mailserver"] = self.object.dnsmxrecord_mailserver.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnsmxrecord")
        )
        context["dnsnsrecord_nameserver"] = self.object.dnsnsrecord_nameserver.annotate(
            max_scan_level=dns_record_scan_level_subquery("dnsnsrecord")
        )

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
class DNSRecordDeleteView(DeleteView):
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


class ScanLevelDeleteView(DeleteView):
    model = ScanLevel
    template_name = "delete_confirm.html"

    def get_success_url(self) -> str:
        return reverse(f"objects:{self.object.object_type}_detail", kwargs={"pk": self.object.object_id})
