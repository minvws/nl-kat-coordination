import threading

import httpx

from scheduler.clients.errors import exception_handler
from scheduler.clients.http import HTTPService
from scheduler.models import Boefje, Organisation, Plugin
from scheduler.utils import dict_utils


class Katalogus(HTTPService):
    """A class that provides methods to interact with the Katalogus API."""

    name = "katalogus"

    def __init__(self, host: str, source: str, timeout: int, pool_connections: int, cache_ttl: int = 30):
        super().__init__(host, source, timeout, pool_connections)

        # For every organisation we cache its plugins, it references the
        # plugin-id as key and the plugin as value.
        self.plugin_cache_lock = threading.Lock()
        self.plugin_cache = dict_utils.ExpiringDict(lifetime=cache_ttl)

        # For every organisation we cache on which type of object (consumes)
        # the boefjes consume, it references the object type (consumes)
        # as the key and a dict of boefjes as value.
        self.boefje_cache_lock = threading.Lock()
        self.boefje_cache = dict_utils.ExpiringDict(lifetime=cache_ttl)

        # For every organisation we cache on which type of object (consumes)
        # the normalizers consume, it references the object type (consumes)
        # as the key and a dict of normalizers as value.
        self.normalizer_cache_lock = threading.Lock()
        self.normalizer_cache = dict_utils.ExpiringDict(lifetime=cache_ttl)

        # For every organisation we cache which new boefjes for an organisation
        # have been enabled.
        self.new_boefjes_cache_lock = threading.Lock()
        self.new_boefjes_cache: dict = {}

        # Initialise the cache.
        self.flush_caches()

    def flush_caches(self) -> None:
        self.flush_plugin_cache()
        self.flush_normalizer_cache()
        self.flush_boefje_cache()

    def flush_plugin_cache(self) -> None:
        self.logger.debug("Flushing the katalogus plugin cache for organisations")

        with self.plugin_cache_lock:
            # First, we reset the cache, to make sure we won't get any ExpiredError
            self.plugin_cache.expiration_enabled = False
            self.plugin_cache.reset()

            orgs = self.get_organisations()
            for org in orgs:
                self.plugin_cache.setdefault(org.id, {})

                plugins = self.get_plugins_by_organisation(org.id)
                self.plugin_cache[org.id] = {plugin.id: plugin for plugin in plugins if plugin.enabled}

            self.plugin_cache.expiration_enabled = True

        self.logger.debug("Flushed the katalogus plugin cache for organisations", plugin_cache=self.plugin_cache.cache)

    def flush_boefje_cache(self) -> None:
        """boefje.consumes -> plugin type boefje"""
        self.logger.debug("Flushing the katalogus boefje type cache for organisations")

        with self.boefje_cache_lock:
            # First, we reset the cache, to make sure we won't get any ExpiredError
            self.boefje_cache.expiration_enabled = False
            self.boefje_cache.reset()

            orgs = self.get_organisations()
            for org in orgs:
                self.boefje_cache[org.id] = {}

                for plugin in self.get_plugins_by_organisation(org.id):
                    if plugin.type != "boefje":
                        continue

                    if plugin.enabled is False:
                        continue

                    if not plugin.consumes:
                        continue

                    # NOTE: backwards compatibility, when it is a boefje the
                    # consumes field is a string field.
                    if isinstance(plugin.consumes, str):
                        self.boefje_cache[org.id].setdefault(plugin.consumes, []).append(plugin)
                        continue

                    for type_ in plugin.consumes:
                        self.boefje_cache[org.id].setdefault(type_, []).append(plugin)

            self.boefje_cache.expiration_enabled = True

        self.logger.debug(
            "Flushed the katalogus boefje type cache for organisations", boefje_cache=self.boefje_cache.cache
        )

    def flush_normalizer_cache(self) -> None:
        """normalizer.consumes -> plugin type normalizer"""
        self.logger.debug("Flushing the katalogus normalizer type cache for organisations")

        with self.normalizer_cache_lock:
            # First, we reset the cache, to make sure we won't get any ExpiredError
            self.normalizer_cache.expiration_enabled = False
            self.normalizer_cache.reset()

            orgs = self.get_organisations()
            for org in orgs:
                self.normalizer_cache[org.id] = {}

                for plugin in self.get_plugins_by_organisation(org.id):
                    if plugin.type != "normalizer":
                        continue

                    if plugin.enabled is False:
                        continue

                    if not plugin.consumes:
                        continue

                    for type_ in plugin.consumes:
                        self.normalizer_cache[org.id].setdefault(type_, []).append(plugin)

            self.normalizer_cache.expiration_enabled = True

        self.logger.debug(
            "Flushed the katalogus normalizer type cache for organisations",
            normalizer_cache=self.normalizer_cache.cache,
        )

    @exception_handler
    def get_boefjes(self) -> list[Boefje]:
        url = f"{self.host}/boefjes"
        try:
            response = self.get(url)
            return [Boefje(**boefje) for boefje in response.json()]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.NOT_FOUND:
                return []
            raise

    @exception_handler
    def get_boefje(self, boefje_id: str) -> Boefje | None:
        url = f"{self.host}/boefjes/{boefje_id}"
        try:
            response = self.get(url)
            return Boefje(**response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.NOT_FOUND:
                return None
            raise

    @exception_handler
    def get_organisation(self, organisation_id) -> Organisation | None:
        url = f"{self.host}/v1/organisations/{organisation_id}"
        try:
            response = self.get(url)
            return Organisation(**response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.NOT_FOUND:
                return None
            raise

    @exception_handler
    def get_organisations(self) -> list[Organisation]:
        url = f"{self.host}/v1/organisations"
        try:
            response = self.get(url)
            return [Organisation(**organisation) for organisation in response.json().values()]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.NOT_FOUND:
                return []
            raise

    @exception_handler
    def get_plugins_by_organisation(self, organisation_id: str) -> list[Plugin]:
        url = f"{self.host}/v1/organisations/{organisation_id}/plugins"
        try:
            response = self.get(url)
            return [Plugin(**plugin) for plugin in response.json()]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.NOT_FOUND:
                return []
            raise

    def get_plugins_by_org_id(self, organisation_id: str) -> list[Plugin]:
        def _get_from_cache() -> list[Plugin]:
            with self.plugin_cache_lock:
                return dict_utils.deep_get(self.plugin_cache, [organisation_id])

        try:
            return _get_from_cache()
        except dict_utils.ExpiredError:
            self.flush_plugin_cache()
            return _get_from_cache()

    def get_plugin_by_id_and_org_id(self, plugin_id: str, organisation_id: str) -> Plugin:
        def _get_from_cache() -> Plugin:
            with self.plugin_cache_lock:
                return dict_utils.deep_get(self.plugin_cache, [organisation_id, plugin_id])

        try:
            if self.plugin_cache.is_empty():
                self.flush_plugin_cache()
            return _get_from_cache()
        except dict_utils.ExpiredError:
            self.flush_plugin_cache()
            return _get_from_cache()

    def get_boefjes_by_type_and_org_id(self, boefje_type: str, organisation_id: str) -> list[Plugin]:
        def _get_from_cache() -> list[Plugin]:
            with self.boefje_cache_lock:
                return dict_utils.deep_get(self.boefje_cache, [organisation_id, boefje_type])

        try:
            if self.boefje_cache.is_empty():
                self.flush_boefje_cache()
            return _get_from_cache()
        except dict_utils.ExpiredError:
            self.flush_boefje_cache()
            return _get_from_cache()

    def get_normalizers_by_org_id_and_type(self, organisation_id: str, normalizer_type: str) -> list[Plugin]:
        def _get_from_cache() -> list[Plugin]:
            with self.normalizer_cache_lock:
                return dict_utils.deep_get(self.normalizer_cache, [organisation_id, normalizer_type])

        try:
            if self.normalizer_cache.is_empty():
                self.flush_normalizer_cache()
            return _get_from_cache()
        except dict_utils.ExpiredError:
            self.flush_normalizer_cache()
            return _get_from_cache()

    def get_new_boefjes_by_org_id(self, organisation_id: str) -> list[Plugin]:
        with self.new_boefjes_cache_lock:
            # Get the enabled boefjes for the organisation from katalogus
            plugins = self.get_plugins_by_organisation(organisation_id)
            enabled_boefjes = {
                plugin.id: plugin
                for plugin in plugins
                if plugin.enabled is True and plugin.type == "boefje" and plugin.consumes
            }

            # Check if there are new boefjes
            new_boefjes = []
            for boefje_id, boefje in enabled_boefjes.items():
                if boefje_id not in self.new_boefjes_cache.get(organisation_id, {}):
                    new_boefjes.append(boefje)

            # Update the cache
            self.new_boefjes_cache[organisation_id] = enabled_boefjes

            self.logger.debug(
                "%d new boefjes found for organisation %s",
                len(new_boefjes),
                organisation_id,
                organisation_id=organisation_id,
                boefjes=[boefje.name for boefje in new_boefjes],
            )

            return new_boefjes
