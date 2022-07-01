from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from fmea.models import FailureMode, FailureModeEffect
from fmea.tools import calculate_risk_class


def recalculate_risk_class(instance, delete=False):
    """
    Recalculate the risk class when FMEA effects changes/deleted for all
    failure modes it belongs to.
    """

    severity_level = 0
    severity_levels = []
    failure_modes = FailureMode.objects.filter(effect=instance)
    for failure_mode in failure_modes:
        frequency_level = failure_mode.frequency_level
        detectability_level = failure_mode.detectability_level
        for effect in failure_mode.effect.all():
            if delete:
                if instance.effect != effect.effect:
                    severity_levels.append(effect.severity_level)
            else:
                severity_levels.append(effect.severity_level)
        if severity_levels:
            severity_level = max(severity_levels)
        risk_class = calculate_risk_class(
            frequency_level, detectability_level, severity_level
        )
        failure_mode.risk_class = risk_class.value
        failure_mode.save()


@receiver(pre_delete, sender=FailureModeEffect)
def failure_mode_effect_pre_deleted(instance, **kwargs):
    """
    This function gets triggered everytime FailureMode effects got
    deleted. It must check all failure modes that is connected to the deleted
    effect(s) and recalculate the risk class. pre_delete is used here,
    otherwise once deleted you don't know which failure modes to check.
    """

    # Got parameter deleted=True to exclude deleted effects
    recalculate_risk_class(instance, delete=True)


@receiver(post_save, sender=FailureModeEffect)
def failure_mode_effect_changed(instance, **kwargs):
    """
    This function gets triggered everytime FailureMode effects got
    updated. It must check all failure modes that is connected to the updated
    effect(s) and recalculate the risk class.
    """

    recalculate_risk_class(instance)
