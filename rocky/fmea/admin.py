from django.contrib import admin

from fmea.forms import FailureModeAffectedObjectForm, FailureModeEffectForm, FailureModeForm

from .models import FailureMode, FailureModeAffectedObject, FailureModeEffect, FailureModeTreeObject


@admin.register(FailureMode)
class FailureModeAdmin(admin.ModelAdmin):
    form = FailureModeForm


@admin.register(FailureModeAffectedObject)
class FailureModeAffectedObjectAdmin(admin.ModelAdmin):
    form = FailureModeAffectedObjectForm


@admin.register(FailureModeTreeObject)
class FailureModeTreeObjectAdmin(admin.ModelAdmin):
    pass


@admin.register(FailureModeEffect)
class FailureModeEffectAdmin(admin.ModelAdmin):
    list_display = (
        "effect",
        "severity_level",
        "id",
    )
    form = FailureModeEffectForm
