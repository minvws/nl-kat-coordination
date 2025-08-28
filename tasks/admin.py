from django.contrib import admin

from tasks.models import Schedule, Task, NewSchedule

admin.site.register(Schedule)
admin.site.register(NewSchedule)
admin.site.register(Task)
