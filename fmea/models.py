from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from fmea.tools import BLANK_CHOICE


class DEPARTMENTS(models.TextChoices):
    FINANCES = "Finances", _("Finances")
    MARKETING = "Marketing", _("Marketing")
    HR = "Human Resources", _("Human Resources")
    R_AND_D = "Research & Development", _("Research & Development")
    ADMIN = "Administration", _("Administration")
    SERVICE = "Service", _("Service")


class SEVERITY_LEVEL(models.IntegerChoices):
    L1 = 1, _("Level 1: Not Severe")
    L2 = 2, _("Level 2: Harmful")
    L3 = 3, _("Level 3: Severe")
    L4 = 4, _("Level 4: Very Harmful")
    L5 = 5, _("Level 5: Catastrophic")


class FREQUENCY_LEVEL(models.IntegerChoices):
    L1 = 1, _("Level 1: Very Rare. Incident (almost) never occurs, almost unthinkable.")
    L2 = 2, _("Level 2: Rare. Incidents occur less than once a year (3-5).")
    L3 = 3, _("Level 3: Occurs. Incidents occur several times a year.")
    L4 = 4, _("Level 4: Regularly. Incidents occur weekly.")
    L5 = 5, _("Level 5: Frequent. Incidents occur daily.")


class DETECTABILITY_LEVEL(models.IntegerChoices):
    L1 = 1, _(
        "Level 1: Always Detectable. Incident (almost) never occurs, almost unthinkable."
    )
    L2 = 2, _(
        "Level 2: Usually Detectable. Incidents occur less than once a year (3-5)."
    )
    L3 = 3, _("Level 3: Detectable. Faillure mode is detectable with effort.")
    L4 = 4, _("Level 4: Poorly Detectable. Detecting the faillure mode is difficult.")
    L5 = 5, _(
        "Level 5: Almost Undetectable. Faillure mode detection is very difficult or nearly impossible."
    )


class FailureModeEffect(models.Model):
    effect = models.TextField(max_length=256, unique=True, blank=False)
    severity_level = models.PositiveSmallIntegerField(
        choices=BLANK_CHOICE + SEVERITY_LEVEL.choices, blank=False
    )

    def __str__(self):
        return self.effect

    def get_absolute_url(self):
        return reverse("fmea_failure_mode_effect_detail", args=[self.pk])

    def get_update_url(self):
        return reverse("fmea_failure_mode_effect_update", args=[self.pk])


class FailureMode(models.Model):
    failure_mode = models.CharField(max_length=256, unique=True, blank=False)
    description = models.CharField(max_length=256, blank=True)
    frequency_level = models.PositiveSmallIntegerField(
        choices=BLANK_CHOICE + FREQUENCY_LEVEL.choices
    )
    detectability_level = models.PositiveSmallIntegerField(
        choices=BLANK_CHOICE + DETECTABILITY_LEVEL.choices
    )
    effect = models.ManyToManyField(FailureModeEffect, blank=False)
    risk_priority_number = models.PositiveSmallIntegerField(default=0)
    critical_score = models.PositiveSmallIntegerField(default=0)
    risk_class = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name_plural = _("Failure modes")

    def __str__(self):
        return self.failure_mode

    def get_absolute_url(self):
        return reverse("fmea_failure_mode_detail", args=[self.pk])

    def get_update_url(self):
        return reverse("fmea_failure_mode_update", args=[self.pk])


class FailureModeAffectedObject(models.Model):
    failure_mode = models.ForeignKey(
        FailureMode,
        on_delete=models.CASCADE,
        null=True,
    )
    affected_department = models.CharField(
        max_length=50, choices=BLANK_CHOICE + DEPARTMENTS.choices
    )
    affected_ooi_type = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = _("Failure Mode Affected Objects")

    def __str__(self):
        return str(self.failure_mode)


class FailureModeTreeObject(models.Model):
    tree_object = models.CharField(max_length=256)
    affected_department = models.CharField(
        max_length=50, choices=BLANK_CHOICE + DEPARTMENTS.choices
    )

    def __str__(self):
        return str(self.tree_object)
