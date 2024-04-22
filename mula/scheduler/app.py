import os
import threading

import structlog
from opentelemetry import trace

from scheduler import context, schedulers, server
from scheduler.connectors.errors import ExternalServiceError
from scheduler.utils import thread

tracer = trace.get_tracer(__name__)


class App:
    """Main application definition for the scheduler implementation of KAT.

    The App is responsible for starting and managing:

        * Schedulers: The schedulers are responsible for managing the queues
        and tasks for a specific organisation.

        * Monitors: The monitors are responsible for monitoring the state of
        the application, and executing procedures based on the state of the
        application.

        * Server: The server is responsible for exposing the application
        through a REST API.

        * Metrics: The collection of application specific metrics.

    Attributes:
        logger:
            The logger for the class.
        ctx:
            Application context of shared data (e.g. configuration, external
            services connections).
        stop_event: A threading.Event object used for communicating a stop
            event across threads.
        schedulers:
            A dict of schedulers, keyed by scheduler id.
        server:
            The http rest api server instance.
    """

    def __init__(self, ctx: context.AppContext) -> None:
        """Initialize the application.

        Args:
            ctx:
                Application context of shared data (e.g. configuration,
                external services connections).
        """

        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.ctx: context.AppContext = ctx

        threading.excepthook = self.unhandled_exception
        self.stop_event: threading.Event = threading.Event()
        self.lock: threading.Lock = threading.Lock()

        self.schedulers: dict[
            str,
            schedulers.Scheduler | schedulers.BoefjeScheduler | schedulers.NormalizerScheduler,
        ] = {}
        self.server: server.Server | None = None

    @tracer.start_as_current_span("monitor_organisations")
    def monitor_organisations(self) -> None:
        """Monitor the organisations from the Katalogus service, and add/remove
        organisations from the schedulers.
        """
        current_schedulers = self.schedulers.copy()

        # We make a difference between the organisation id's that are used
        # by the schedulers, and the organisation id's that are in the
        # Katalogus service. We will add/remove schedulers based on the
        # difference between these two sets.
        scheduler_orgs: set[str] = {
            s.organisation.id for s in current_schedulers.values() if hasattr(s, "organisation")
        }
        try:
            orgs = self.ctx.services.katalogus.get_organisations()
        except ExternalServiceError:
            self.logger.exception("Failed to get organisations from Katalogus")
            return

        katalogus_orgs = {org.id for org in orgs}

        additions = katalogus_orgs.difference(scheduler_orgs)
        self.logger.debug("Organisations to add: %s", len(additions), additions=sorted(additions))

        removals = scheduler_orgs.difference(katalogus_orgs)
        self.logger.debug("Organisations to remove: %s", len(removals), removals=sorted(removals))

        # We need to get scheduler ids of the schedulers that are associated
        # with the removed organisations
        removal_scheduler_ids: set[str] = {
            s.scheduler_id
            for s in current_schedulers.values()
            if hasattr(s, "organisation") and s.organisation.id in removals
        }

        # Remove schedulers for removed organisations
        for scheduler_id in removal_scheduler_ids:
            if scheduler_id not in self.schedulers:
                continue

            self.schedulers[scheduler_id].stop()

        if removals:
            self.logger.debug(
                "Removed %s organisations from scheduler",
                len(removals),
                removals=sorted(removals),
            )

        # Add schedulers for organisation
        for org_id in additions:
            try:
                org = self.ctx.services.katalogus.get_organisation(org_id)
            except ExternalServiceError as e:
                self.logger.error("Failed to get organisation from Katalogus", error=e, org_id=org_id)
                continue

            scheduler_boefje = schedulers.BoefjeScheduler(
                ctx=self.ctx,
                scheduler_id=f"boefje-{org.id}",
                organisation=org,
                callback=self.remove_scheduler,
            )

            scheduler_normalizer = schedulers.NormalizerScheduler(
                ctx=self.ctx,
                scheduler_id=f"normalizer-{org.id}",
                organisation=org,
                callback=self.remove_scheduler,
            )

            with self.lock:
                self.schedulers[scheduler_boefje.scheduler_id] = scheduler_boefje
                self.schedulers[scheduler_normalizer.scheduler_id] = scheduler_normalizer

            scheduler_normalizer.run()
            scheduler_boefje.run()

        if additions:
            # Flush katalogus caches when new organisations are added
            self.ctx.services.katalogus.flush_caches()

            self.logger.debug(
                "Added %s organisations to scheduler",
                len(additions),
                additions=sorted(additions),
            )

    @tracer.start_as_current_span("collect_metrics")
    def collect_metrics(self) -> None:
        """Collect application metrics

        This method that allows to collect metrics throughout the application.
        """
        with self.lock:
            for s in self.schedulers.copy().values():
                self.ctx.metrics_qsize.labels(
                    scheduler_id=s.scheduler_id,
                ).set(
                    s.queue.qsize(),
                )

                status_counts = self.ctx.datastores.task_store.get_status_counts(s.scheduler_id)
                for status, count in status_counts.items():
                    self.ctx.metrics_task_status_counts.labels(
                        scheduler_id=s.scheduler_id,
                        status=status,
                    ).set(
                        count,
                    )

    def start_schedulers(self) -> None:
        # Initialize the schedulers
        try:
            orgs = self.ctx.services.katalogus.get_organisations()
        except ExternalServiceError as e:
            self.logger.error("Failed to get organisations from Katalogus", error=e)
            return

        for org in orgs:
            boefje_scheduler = schedulers.BoefjeScheduler(
                ctx=self.ctx,
                scheduler_id=f"boefje-{org.id}",
                organisation=org,
                callback=self.remove_scheduler,
            )
            self.schedulers[boefje_scheduler.scheduler_id] = boefje_scheduler

            normalizer_scheduler = schedulers.NormalizerScheduler(
                ctx=self.ctx,
                scheduler_id=f"normalizer-{org.id}",
                organisation=org,
                callback=self.remove_scheduler,
            )
            self.schedulers[normalizer_scheduler.scheduler_id] = normalizer_scheduler

        # Start schedulers
        for scheduler in self.schedulers.values():
            scheduler.run()

    def start_monitors(self) -> None:
        thread.ThreadRunner(
            name="App-monitor_organisations",
            target=self.monitor_organisations,
            stop_event=self.stop_event,
            interval=self.ctx.config.monitor_organisations_interval,
        ).start()

    def start_collectors(self) -> None:
        thread.ThreadRunner(
            name="App-metrics_collector",
            target=self.collect_metrics,
            stop_event=self.stop_event,
            interval=10,
        ).start()

    def start_server(self) -> None:
        self.server = server.Server(self.ctx, self.schedulers)
        thread.ThreadRunner(
            name="App-server",
            target=self.server.run,
            stop_event=self.stop_event,
            loop=False,
        ).start()

    def run(self) -> None:
        """Start the main scheduler application, and run in threads the
        following processes:

            * schedulers
            * monitors
            * metrics collecting
            * api server
        """
        # Start schedulers
        self.start_schedulers()

        # Start monitors
        self.start_monitors()

        # Start metrics collecting
        if self.ctx.config.collect_metrics:
            self.start_collectors()

        # API Server
        self.start_server()

        # Main thread
        while not self.stop_event.is_set():
            self.stop_event.wait()

        # When the stop event is set, we want to gracefully shutdown the
        # rest of the application.
        self.shutdown()

        # We're calling this here, because we want to issue a shutdown from
        # within a thread, otherwise it will not exit a docker container.
        # Source: https://stackoverflow.com/a/1489838/1346257
        os._exit(1)

    def shutdown(self) -> None:
        """Shutdown the scheduler application, and all threads."""
        self.logger.info("Shutdown initiated")

        self.stop_event.set()

        # First stop schedulers
        for s in self.schedulers.copy().values():
            s.stop()

        # Stop all threads that are still running, except the main thread.
        # These threads likely have a blocking call and as such are not able
        # to leverage a stop event.
        self.stop_threads()

        self.logger.info("Shutdown complete")

    def stop_threads(self) -> None:
        """Stop all threads, except the main thread."""
        for t in threading.enumerate():
            if t is threading.current_thread():
                continue

            if t is threading.main_thread():
                continue

            if not t.is_alive():
                continue

            t.join(5)

    def unhandled_exception(self, args: threading.ExceptHookArgs) -> None:
        """Gracefully shutdown the scheduler application, and all threads
        when a unhandled exception occurs.
        """
        self.logger.error("Unhandled exception occurred: %s", args.exc_value)
        self.stop_event.set()

    def remove_scheduler(self, scheduler_id: str) -> None:
        """Remove a scheduler from the application. This method is passed
        as a callback to the scheduler, so that the scheduler can remove
        itself from the application.

        Args:
            scheduler_id: The id of the scheduler to remove.
        """
        with self.lock:
            if scheduler_id not in self.schedulers:
                return

            self.schedulers.pop(scheduler_id)
