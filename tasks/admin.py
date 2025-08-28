from django.contrib import admin

from tasks.models import NewSchedule, Schedule, Task

admin.site.register(Schedule)
admin.site.register(NewSchedule)
admin.site.register(Task)
