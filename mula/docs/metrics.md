# Metrics

The scheduler implements OpenTelemetry to expose metrics for monitoring and
observability purposes. Next to supporting tracing, it also exposes several
metrics from its `/metrics` endpoint. These metrics can be used to monitor the
performance and health of the scheduler. These metrics can be collected and
visualized by using a monitoring system like Prometheus.

To enable metrics collection, add `SCHEDULER_COLLECT_METRICS=true` to
your `.env` file.

The following is a detailed explanation of the scheduler metrics:

| Metric                       | Description                                                               |
| ---------------------------- | ------------------------------------------------------------------------- |
| scheduler_qsize              | The number of items that are queued on a scheduler queue per organization |
| scheduler_task_status_counts | The number of tasks per status, per organization                          |

Refer to the [architecture.md](./architecture.md) document what the different
statuses means, in relation to a task that is scheduled and flows through
the system.
