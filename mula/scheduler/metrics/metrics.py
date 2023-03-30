from prometheus_client import CollectorRegistry, Gauge, Info
from scheduler import context


class Metrics:
    def __init__(self, ctx: context.AppContext) -> None:
        self.ctx = ctx
        self.registry = CollectorRegistry()

        self.info = Info("scheduler_settings", "Scheduler configuration settings", registry=self.registry,).info(
            {
                "monitor_organisations_interval": str(self.ctx.config.monitor_organisations_interval),
                "pq_maxsize": str(self.ctx.config.pq_maxsize),
                "pq_populate_interval": str(self.ctx.config.pq_populate_interval),
                "pq_populate_grace_period": str(self.ctx.config.pq_populate_grace_period),
                "pq_populate_max_random_objects": str(self.ctx.config.pq_populate_max_random_objects),
            }
        )
