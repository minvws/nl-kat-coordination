from django import forms
from django.utils.translation import gettext_lazy as _
from katalogus.models import Source


class SourceForm(forms.ModelForm):
    class Meta:
        model = Source

        fields = "__all__"
