# Metrics

The scheduler implements OpenTelemetry to expose metrics for monitoring and
observability purposes. Next to supporting tracing, it also exposes several
metrics from its `/metrics` endpoint. These metrics can be used to monitor the
performance and health of the scheduler. These metrics can be collected and
visualized by using a monitoring system like Prometheus.

The following is a detailed explanation of the scheduler metrics:

| Metric                       | Description                                                               |
| ---------------------------- | ------------------------------------------------------------------------- |
| scheduler_cpu_usage          | The CPU usage of the scheduler.                                           |
| scheduler_memory_usage       | The memory usage of the scheduler                                         |
| scheduler_qsize              | The number of items that are queued on a scheduler queue per organization |
| scheduler_task_status_counts | The number of tasks per status, per organization                          |

Refer to the [architecture.md](./architecture.md) document what the different
statuses means, in relation to a task that is scheduled and flows through
the system.
