from django.contrib import admin

from katalogus.models import Boefje, BoefjeConfig, Normalizer, NormalizerConfig

admin.site.register(Boefje)
admin.site.register(BoefjeConfig)
admin.site.register(Normalizer)
admin.site.register(NormalizerConfig)
