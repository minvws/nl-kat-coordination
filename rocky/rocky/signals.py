from django.dispatch import Signal

task_received = Signal()
task_succeeded = Signal()
task_failed = Signal()
