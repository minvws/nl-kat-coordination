import logging
import os
import threading
import time
from typing import Dict

from opentelemetry import trace

from scheduler import context, queues, rankers, schedulers, server
from scheduler.connectors import listeners
from scheduler.models import BoefjeTask, NormalizerTask, Organisation
from scheduler.utils import thread

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class App:
    """Main application definition for the scheduler implementation of KAT.

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
        listeners:
            A dict of connector.Listener instances.
        server:
            A server.Server instance that handles the API server.
    """

    def __init__(self, ctx: context.AppContext) -> None:
        """Initialize the application.

        Args:
            ctx:
                Application context of shared data (e.g. configuration,
                external services connections).
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.stop_event: threading.Event = threading.Event()
        self.lock: threading.Lock = threading.Lock()

        # Initialize schedulers
        self.schedulers: Dict[str, schedulers.Scheduler] = {}

        self.initialize_boefje_schedulers()
        self.initialize_normalizer_schedulers()

        # Initialize listeners
        self.listeners: Dict[str, listeners.Listener] = {}

        # Initialize API server
        self.server: server.Server = server.Server(self.ctx, self.schedulers)

    def initialize_boefje_schedulers(self) -> None:
        """Initialize the schedulers for the Boefje tasks. We will create
        schedulers for all organisations in the Katalogus service.
        """
        orgs = self.ctx.services.katalogus.get_organisations()
        for org in orgs:
            s = self.create_boefje_scheduler(org)
            self.schedulers[s.scheduler_id] = s

    def initialize_normalizer_schedulers(self) -> None:
        """Initialize the schedulers for the Normalizer tasks. We will create
        schedulers for all organisations in the Katalogus service.
        """
        orgs = self.ctx.services.katalogus.get_organisations()
        for org in orgs:
            s = self.create_normalizer_scheduler(org)
            self.schedulers[s.scheduler_id] = s

    def create_normalizer_scheduler(self, org: Organisation) -> schedulers.NormalizerScheduler:
        """Create a normalizer scheduler for the given organisation."""
        identifier = f"normalizer-{org.id}"

        queue = queues.NormalizerPriorityQueue(
            pq_id=identifier,
            maxsize=self.ctx.config.pq_maxsize,
            item_type=NormalizerTask,
            allow_priority_updates=True,
            pq_store=self.ctx.pq_store,
        )

        ranker = rankers.NormalizerRanker(
            ctx=self.ctx,
        )

        scheduler = schedulers.NormalizerScheduler(
            ctx=self.ctx,
            scheduler_id=identifier,
            queue=queue,
            ranker=ranker,
            populate_queue_enabled=self.ctx.config.normalizer_populate,
            organisation=org,
        )

        return scheduler

    def create_boefje_scheduler(self, org: Organisation) -> schedulers.BoefjeScheduler:
        """Create a scheduler for the given organisation.

        Args:
            org: The organisation to create a scheduler for.
        """
        identifier = f"boefje-{org.id}"

        queue = queues.BoefjePriorityQueue(
            pq_id=identifier,
            maxsize=self.ctx.config.pq_maxsize,
            item_type=BoefjeTask,
            allow_priority_updates=True,
            pq_store=self.ctx.pq_store,
        )

        ranker = rankers.BoefjeRanker(
            ctx=self.ctx,
        )

        scheduler = schedulers.BoefjeScheduler(
            ctx=self.ctx,
            scheduler_id=identifier,
            queue=queue,
            ranker=ranker,
            populate_queue_enabled=self.ctx.config.boefje_populate,
            organisation=org,
        )

        return scheduler

    @tracer.start_as_current_span("monitor_organisations")
    def monitor_organisations(self) -> None:
        """Monitor the organisations from the Katalogus service, and add/remove
        organisations from the schedulers.
        """
        current_schedulers = self.schedulers.copy()
        scheduler_orgs = {s.organisation.id for s in current_schedulers.values()}
        katalogus_orgs = {org.id for org in self.ctx.services.katalogus.get_organisations()}

        additions = katalogus_orgs.difference(scheduler_orgs)
        self.logger.debug("Organisations to add: %s", len(additions))

        removals = scheduler_orgs.difference(katalogus_orgs)
        self.logger.debug("Organisations to remove: %s", len(removals))

        # Get scheduler ids for removals
        removal_scheduler_ids = []
        for s in current_schedulers.values():
            if s.organisation.id in removals:
                removal_scheduler_ids.append(s.scheduler_id)

        # Remove schedulers for organisation
        for scheduler_id in removal_scheduler_ids:
            with self.lock:
                if scheduler_id not in self.schedulers:
                    continue

                self.schedulers[scheduler_id].stop()
                self.schedulers.pop(scheduler_id)

        if removals:
            self.logger.info(
                "Removed %s organisations from scheduler [org_ids=%s]",
                len(removals),
                removals,
            )

        # Add schedulers for organisation
        for org_id in additions:
            org = self.ctx.services.katalogus.get_organisation(org_id)

            scheduler_normalizer = self.create_normalizer_scheduler(org)
            self.schedulers[scheduler_normalizer.scheduler_id] = scheduler_normalizer
            scheduler_normalizer.run()

            scheduler_boefje = self.create_boefje_scheduler(org)
            self.schedulers[scheduler_boefje.scheduler_id] = scheduler_boefje
            scheduler_boefje.run()

        if additions:
            # Flush katalogus caches when new organisations are added
            self.ctx.services.katalogus.flush_caches()

            self.logger.info(
                "Added %s organisations to scheduler [org_ids=%s]",
                len(additions),
                additions,
            )

    def collect_metrics(self) -> None:
        """Collect application metrics

        This method that allows to collect metrics throughout the application.
        """
        # Collect metrics from the schedulers
        for s in self.schedulers.values():
            self.ctx.metrics_qsize.labels(
                scheduler_id=s.scheduler_id,
            ).set(
                s.queue.qsize(),
            )

    def run(self) -> None:
        """Start the main scheduler application, and run in threads the
        following processes:

            * api server
            * listeners
            * schedulers
            * monitors
            * metrics collecting
        """
        # API Server
        thread.ThreadRunner(
            name="server",
            target=self.server.run,
            stop_event=self.stop_event,
        ).start()

        # Start the listeners
        for name, listener in self.listeners.items():
            thread.ThreadRunner(
                name=f"listener_{name}",
                target=listener.listen,
                stop_event=self.stop_event,
            ).start()

        # Start the schedulers
        for scheduler in self.schedulers.values():
            scheduler.run()

        # Start monitors
        thread.ThreadRunner(
            name="monitor_organisations",
            target=self.monitor_organisations,
            stop_event=self.stop_event,
            interval=self.ctx.config.monitor_organisations_interval,
        ).start()

        # Start metrics collecting
        thread.ThreadRunner(
            name="metrics_collector",
            target=self.collect_metrics,
            stop_event=self.stop_event,
            interval=1,
        ).start()

        # Main thread
        while not self.stop_event.is_set():
            time.sleep(0.01)


def shutdown(args) -> None:
    """Gracefully shutdown the scheduler application, and all threads."""
    logger.info("Shutting down...")

    for t in threading.enumerate():
        if t is threading.current_thread():
            continue

        if t is threading.main_thread():
            continue

        if not t.is_alive():
            continue

        t.join(5)

    logger.info("Shutdown complete")

    # We're calling this here, because we want to issue a shutdown from
    # within a thread, otherwise it will not exit a docker container.
    # Source: https://stackoverflow.com/a/1489838/1346257
    os._exit(1)


# When a unhanded exception occurs, we want to shutdown the application
threading.excepthook = shutdown
