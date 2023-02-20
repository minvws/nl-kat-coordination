"""Main application class for Octopoes.

This class is responsible for starting the application, monitoring organisations and running subthreads for each.
"""

import logging
import os
import threading
import time
from typing import Any, Callable, Dict

from octopoes.context.context import AppContext
from octopoes.ingesters.ingester import Ingester
from octopoes.models.organisation import Organisation
from octopoes.server import server
from octopoes.utils import thread


class App:
    """Main application definition for Octopoes.

    Attributes:
        logger:
            The logger for the class.
        ctx:
            Application context of shared data (e.g. configuration, external
            services connections).
        threads:
            A dict of ThreadRunner instances, used for runner processes
            concurrently.
        stop_event: A threading.Event object used for communicating a stop
            event across threads.
        ingesters:
            A dict of connector.Listener instances.
        # server:
        #     A server.Server instance that handles the API server.
    """

    organisation: Organisation

    def __init__(self, ctx: AppContext) -> None:
        """Initialize the application.

        Args:
            ctx:
                Application context of shared data (e.g. configuration,
                external services connections).
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: AppContext = ctx
        self.threads: Dict[str, thread.ThreadRunner] = {}
        self.stop_event: threading.Event = self.ctx.stop_event

        # Initialize ingesters
        self.ingesters: Dict[str, Ingester] = {}
        self.initialize_ingesters()

        # Initialize API server
        self.server: server.Server = server.Server(self.ctx, self.ingesters)

    def shutdown(self) -> None:
        """Gracefully shutdown octopoes, and all threads."""
        self.logger.info("Shutting down...")

        for ingester in self.ingesters.values():
            ingester.stop()

        for thread_ in self.threads.values():
            thread_.join(5)

        self.logger.info("Shutdown complete")

        # We're calling this here, because we want to issue a shutdown from
        # within a thread, otherwise it will not exit a docker container.
        # Source: https://stackoverflow.com/a/1489838/1346257
        os._exit(1)  # pylint: disable=protected-access

    def _run_in_thread(
        self,
        name: str,
        func: Callable[[], Any],
        interval: float = 0.01,
        daemon: bool = False,
    ) -> None:
        """Make a function run in a thread, and add it to the dict of threads.

        Args:
            name: The name of the thread.
            func: The function to run in the thread.
            interval: The interval to run the function.
            daemon: Whether the thread should be a daemon.
        """
        self.threads[name] = thread.ThreadRunner(
            target=func,
            stop_event=self.stop_event,
            interval=interval,
            daemon=daemon,
        )
        self.threads[name].start()

    def initialize_ingesters(self) -> None:
        """Initialize the ingesters for the Boefje tasks.

        We will create ingesters for all organisations in the Katalogus service.
        """
        orgs = self.ctx.services.katalogus.get_organisations()
        for org in orgs:
            ingester = self.create_ingester(org)
            self.ingesters[ingester.ingester_id] = ingester

    def create_ingester(self, org: Organisation) -> Ingester:
        """Create an ingesters for the given organisation.

        Args:
            org: The organisation to create an ingesters for.
        """
        return Ingester(self.ctx, f"{org.id}", organisation=org)

    def monitor_organisations(self) -> None:
        """Monitor the organisations in the Katalogus service, and add/remove organisations from the ingesters."""
        ingester_orgs = {s.organisation.id for s in self.ingesters.values()}
        katalogus_orgs = {org.id for org in self.ctx.services.katalogus.get_organisations()}

        self.logger.debug("Monitoring organisations: %s", katalogus_orgs)

        additions = katalogus_orgs.difference(ingester_orgs)
        removals = ingester_orgs.difference(katalogus_orgs)

        for org_id in removals:
            for ingester in self.ingesters.values():
                if ingester.organisation.id != org_id:
                    continue

                del self.ingesters[ingester.ingester_id]
                break

        self.logger.info("Removed %s organisations from ingesters [org_ids=%s]", len(removals), removals)

        for org_id in additions:
            org = self.ctx.services.katalogus.get_organisation(org_id)

            ingester = self.create_ingester(org)
            self.ingesters[ingester.ingester_id] = ingester

        self.logger.info("Added %s organisations to ingesters [org_ids=%s]", len(additions), additions)

    def run(self) -> None:
        """Start the Octopoes application, and run in threads the following processes.

        * api server
        * ingesters
        * monitors
        """
        # API Server
        self._run_in_thread(name="server", func=self.server.run, daemon=False)

        # Start the ingesters
        for ingester in self.ingesters.values():
            ingester.run()

        # Start monitors
        self._run_in_thread(name="monitor_organisations", func=self.monitor_organisations, interval=60)

        # Main thread
        while not self.stop_event.is_set():
            try:
                time.sleep(0.01)
            except KeyboardInterrupt:
                break

        self.shutdown()
