from django.contrib import admin

from fmea.forms import (
    FailureModeForm,
    FailureModeAffectedObjectForm,
    FailureModeEffectForm,
)
from .models import (
    FailureMode,
    FailureModeAffectedObject,
    FailureModeTreeObject,
    FailureModeEffect,
)


class FailureModeAdmin(admin.ModelAdmin):
    form = FailureModeForm


class FailureModeAffectedObjectAdmin(admin.ModelAdmin):
    form = FailureModeAffectedObjectForm


class FailureModeTreeObjectAdmin(admin.ModelAdmin):
    pass


class FailureModeEffectAdmin(admin.ModelAdmin):
    list_display = (
        "effect",
        "severity_level",
        "id",
    )
    form = FailureModeEffectForm


admin.site.register(FailureMode, FailureModeAdmin)
admin.site.register(FailureModeAffectedObject, FailureModeAffectedObjectAdmin)
admin.site.register(FailureModeTreeObject, FailureModeTreeObjectAdmin)
admin.site.register(FailureModeEffect, FailureModeEffectAdmin)
