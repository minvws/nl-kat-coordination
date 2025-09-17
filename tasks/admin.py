from django.contrib import admin

from tasks.models import Schedule, Task

admin.site.register(Schedule)
admin.site.register(Task)
