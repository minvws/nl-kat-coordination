from django.contrib import admin
from katalogus.forms import SourceForm
from katalogus.models import Source


class SourceAdmin(admin.ModelAdmin):
    form = SourceForm


admin.site.register(Source, SourceAdmin)
