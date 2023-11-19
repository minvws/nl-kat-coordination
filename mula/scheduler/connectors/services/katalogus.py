from typing import Dict, List

from scheduler.connectors.errors import exception_handler
from scheduler.models import Boefje, Organisation, Plugin
from scheduler.utils import dict_utils

from .services import HTTPService


class Katalogus(HTTPService):
    """A class that provides methods to interact with the Katalogus API."""

    name = "katalogus"

    def __init__(self, host: str, source: str, timeout: int, pool_connections: int, cache_ttl: int = 30):
        super().__init__(host, source, timeout, pool_connections)

        # For every organisation we cache its plugins, it references the
        # plugin-id as key and the plugin as value.
        self.organisations_plugin_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict(lifetime=cache_ttl)

        # For every organisation we cache on which type of object (consumes)
        # the boefjes consume, it references the object type (consumes)
        # as the key and a dict of boefjes as value.
        self.organisations_boefje_type_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict(lifetime=cache_ttl)

        # For every organisation we cache on which type of object (consumes)
        # the normalizers consume, it references the object type (consumes)
        # as the key and a dict of normalizers as value.
        self.organisations_normalizer_type_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict(lifetime=cache_ttl)

        # For every organisation we cache which new boefjes for an organisation
        # have been enabled.
        self.organisations_new_boefjes_cache: Dict = {}

        # Initialise the cache.
        self.flush_caches()

    def flush_caches(self) -> None:
        self.flush_organisations_plugin_cache()
        self.flush_organisations_normalizer_type_cache()
        self.flush_organisations_boefje_type_cache()

    def flush_organisations_plugin_cache(self) -> None:
        self.logger.debug("flushing plugin cache [cache=%s]", self.organisations_plugin_cache.cache)

        # First, we reset the cache, to make sure we won't get any ExpiredError
        self.organisations_plugin_cache.expiration_enabled = False
        self.organisations_plugin_cache.reset()

        orgs = self.get_organisations()
        for org in orgs:
            if org.id not in self.organisations_plugin_cache:
                self.organisations_plugin_cache[org.id] = {}
                self.organisations_new_boefjes_cache[org.id] = {}

            plugins = self.get_plugins_by_organisation(org.id)
            self.organisations_plugin_cache[org.id] = {plugin.id: plugin for plugin in plugins if plugin.enabled}

        self.organisations_plugin_cache.expiration_enabled = True
        self.logger.debug("flushed plugins cache [cache=%s]", self.organisations_plugin_cache.cache)

    def flush_organisations_boefje_type_cache(self) -> None:
        """boefje.consumes -> plugin type boefje"""
        self.logger.debug("flushing boefje cache [cache=%s]", self.organisations_boefje_type_cache.cache)

        # First, we reset the cache, to make sure we won't get any ExpiredError
        self.organisations_boefje_type_cache.expiration_enabled = False
        self.organisations_boefje_type_cache.reset()

        orgs = self.get_organisations()
        for org in orgs:
            self.organisations_boefje_type_cache[org.id] = {}

            for plugin in self.get_plugins_by_organisation(org.id):
                if plugin.type != "boefje":
                    continue

                if plugin.enabled is False:
                    continue

                # NOTE: backwards compatibility, when it is a boefje the
                # consumes field is a string field.
                if isinstance(plugin.consumes, str):
                    self.organisations_boefje_type_cache[org.id].setdefault(plugin.consumes, []).append(plugin)
                    continue

                for type_ in plugin.consumes:
                    self.organisations_boefje_type_cache[org.id].setdefault(type_, []).append(plugin)

        self.organisations_boefje_type_cache.expiration_enabled = True
        self.logger.debug("flushed boefje cache [cache=%s]", self.organisations_boefje_type_cache.cache)

    def flush_organisations_normalizer_type_cache(self) -> None:
        """normalizer.consumes -> plugin type normalizer"""
        self.logger.debug("flushing normalizer cache [cache=%s]", self.organisations_normalizer_type_cache.cache)

        # First, we reset the cache, to make sure we won't get any ExpiredError
        self.organisations_normalizer_type_cache.expiration_enabled = False
        self.organisations_normalizer_type_cache.reset()

        orgs = self.get_organisations()
        for org in orgs:
            self.organisations_normalizer_type_cache[org.id] = {}

            for plugin in self.get_plugins_by_organisation(org.id):
                if plugin.type != "normalizer":
                    continue

                if plugin.enabled is False:
                    continue

                for type_ in plugin.consumes:
                    self.organisations_normalizer_type_cache[org.id].setdefault(type_, []).append(plugin)

        self.organisations_normalizer_type_cache.expiration_enabled = True
        self.logger.debug("flushed normalizer cache [cache=%s]", self.organisations_normalizer_type_cache.cache)

    @exception_handler
    def get_boefjes(self) -> List[Boefje]:
        url = f"{self.host}/boefjes"
        response = self.get(url)
        return [Boefje(**boefje) for boefje in response.json()]

    @exception_handler
    def get_boefje(self, boefje_id: str) -> Boefje:
        url = f"{self.host}/boefjes/{boefje_id}"
        response = self.get(url)
        return Boefje(**response.json())

    @exception_handler
    def get_organisation(self, organisation_id) -> Organisation:
        url = f"{self.host}/v1/organisations/{organisation_id}"
        response = self.get(url)
        return Organisation(**response.json())

    @exception_handler
    def get_organisations(self) -> List[Organisation]:
        url = f"{self.host}/v1/organisations"
        response = self.get(url)
        return [Organisation(**organisation) for organisation in response.json().values()]

    def get_plugins_by_organisation(self, organisation_id: str) -> List[Plugin]:
        url = f"{self.host}/v1/organisations/{organisation_id}/plugins"
        response = self.get(url)
        return [Plugin(**plugin) for plugin in response.json()]

    def get_plugins_by_org_id(self, organisation_id: str) -> List[Plugin]:
        try:
            return dict_utils.deep_get(self.organisations_plugin_cache, [organisation_id])
        except dict_utils.ExpiredError:
            self.flush_organisations_plugin_cache()
            return dict_utils.deep_get(self.organisations_plugin_cache, [organisation_id])

    def get_plugin_by_id_and_org_id(self, plugin_id: str, organisation_id: str) -> Plugin:
        try:
            return dict_utils.deep_get(self.organisations_plugin_cache, [organisation_id, plugin_id])
        except dict_utils.ExpiredError:
            self.flush_organisations_plugin_cache()
            return dict_utils.deep_get(self.organisations_plugin_cache, [organisation_id, plugin_id])

    def get_boefjes_by_type_and_org_id(self, boefje_type: str, organisation_id: str) -> List[Plugin]:
        try:
            return dict_utils.deep_get(self.organisations_boefje_type_cache, [organisation_id, boefje_type])
        except dict_utils.ExpiredError:
            self.flush_organisations_boefje_type_cache()
            return dict_utils.deep_get(self.organisations_boefje_type_cache, [organisation_id, boefje_type])

    def get_normalizers_by_org_id_and_type(self, organisation_id: str, normalizer_type: str) -> List[Plugin]:
        try:
            return dict_utils.deep_get(self.organisations_normalizer_type_cache, [organisation_id, normalizer_type])
        except dict_utils.ExpiredError:
            self.flush_organisations_normalizer_type_cache()
            return dict_utils.deep_get(self.organisations_normalizer_type_cache, [organisation_id, normalizer_type])

    def get_new_boefjes_by_org_id(self, organisation_id: str) -> List[Plugin]:
        # Get the enabled boefjes for the organisation from katalogus
        plugins = self.get_plugins_by_organisation(organisation_id)
        enabled_boefjes = {
            plugin.id: plugin for plugin in plugins if plugin.enabled is True and plugin.type == "boefje"
        }

        # Check if there are new boefjes
        new_boefjes = []
        for boefje_id, boefje in enabled_boefjes.items():
            if boefje_id in self.organisations_new_boefjes_cache.get(organisation_id, {}):
                continue

            new_boefjes.append(boefje)

        self.organisations_new_boefjes_cache[organisation_id] = enabled_boefjes

        self.logger.debug(
            "%d new boefjes found [organisation_id=%s, new_boefjes=%s]", len(new_boefjes), organisation_id, new_boefjes
        )

        return new_boefjes
