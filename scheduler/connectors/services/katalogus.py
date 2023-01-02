from typing import Dict, List

from scheduler.connectors.errors import exception_handler
from scheduler.models import Boefje, Organisation, Plugin
from scheduler.utils import dict_utils

from .services import HTTPService


class Katalogus(HTTPService):
    name = "katalogus"

    def __init__(self, host: str, source: str, timeout: int = 5):
        super().__init__(host, source, timeout)

        # Example:
        #
        # {
        #     "organisation_id": {
        #          "plugin-id": {}
        #     }
        # }
        self.organisations_plugin_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict(lifetime=30)

        # Example:
        #
        # {
        #     "organisation_id": {
        #         "plugin-type": {
        #             "plugin-id": {}
        #         }
        #     }
        # }
        self.organisations_boefje_type_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict(lifetime=30)
        self.organisations_normalizer_type_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict(lifetime=30)

        # Example:
        #
        # {
        #     "organisation_id": {
        #          "plugin-id": {}
        #     }
        # }
        self.organisations_new_boefjes_cache: Dict = {}

        # Initialize the caches
        self._flush_organisations_plugin_cache()
        self._flush_organisations_normalizer_type_cache()
        self._flush_organisations_boefje_type_cache()

    def _flush_organisations_plugin_cache(self) -> None:
        self.logger.debug("flushing plugin cache [cache=%s]", self.organisations_plugin_cache.cache)
        orgs = self.get_organisations()

        for org in orgs:
            if org.id not in self.organisations_plugin_cache:
                self.organisations_plugin_cache[org.id] = {}

            plugins = self.get_plugins_by_organisation(org.id)
            for plugin in plugins:
                if plugin.id in self.organisations_plugin_cache[org.id]:
                    continue

                # Add new boefje to organisation plugin cache and new boefjes cache
                self.organisations_plugin_cache[org.id][plugin.id] = plugin

                # Add new boefje to new boefjes cache
                self.organisations_new_boefjes_cache.setdefault(org.id, {})[plugin.id] = plugin

    def _flush_organisations_boefje_type_cache(self) -> None:
        """boefje.consumes -> plugin type boefje"""
        self.logger.debug("flushing boefje cache [cache=%s]", self.organisations_boefje_type_cache.cache)
        orgs = self.get_organisations()

        for org in orgs:
            self.organisations_boefje_type_cache[org.id] = {}

            for plugin in self.get_plugins_by_organisation(org.id):
                if plugin.type != "boefje" and plugin.enabled is False: # TODO: CHECK THIS enabled
                    continue

                for type_ in plugin.consumes:
                    self.organisations_boefje_type_cache[org.id].setdefault(type_, []).append(plugin)

        self.logger.debug("flushed boefje cache [cache=%s]", self.organisations_boefje_type_cache.cache)

    def _flush_organisations_normalizer_type_cache(self) -> None:
        """normalizer.consumes -> plugin type normalizer"""
        self.logger.debug("flushing normalizer cache [cache=%s]", self.organisations_normalizer_type_cache.cache)
        orgs = self.get_organisations()

        for org in orgs:
            self.organisations_normalizer_type_cache[org.id] = {}

            for plugin in self.get_plugins_by_organisation(org.id):
                if plugin.type != "normalizer" and plugin.enabled is False:  # TODO: CHECK THIS enabled
                    continue

                for type_ in plugin.consumes:
                    self.organisations_normalizer_type_cache[org.id].setdefault(type_, []).append(plugin)

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

    def get_plugin_by_id_and_org_id(self, plugin_id: str, organisation_id: str) -> Plugin:
        try:
            return dict_utils.deep_get(self.organisations_plugin_cache, [organisation_id, plugin_id])
        except dict_utils.ExpiredError:
            self._flush_organisations_plugin_cache()
            return dict_utils.deep_get(self.organisations_plugin_cache, [organisation_id, plugin_id])

    def get_boefjes_by_type_and_org_id(self, boefje_type: str, organisation_id: str) -> List[Plugin]:
        try:
            return dict_utils.deep_get(self.organisations_boefje_type_cache, [organisation_id, boefje_type])
        except dict_utils.ExpiredError:
            self._flush_organisations_boefje_type_cache()
            return dict_utils.deep_get(self.organisations_boefje_type_cache, [organisation_id, boefje_type])

    def get_normalizers_by_org_id_and_type(self, organisation_id: str, normalizer_type: str) -> List[Plugin]:
        try:
            return dict_utils.deep_get(self.organisations_normalizer_type_cache, [organisation_id, normalizer_type])
        except dict_utils.ExpiredError:
            self._flush_organisations_normalizer_type_cache()
            return dict_utils.deep_get(self.organisations_normalizer_type_cache, [organisation_id, normalizer_type])

    def get_new_boefjes_by_org_id(self, organisation_id: str) -> List[Plugin]:
        new_boefjes = self.organisations_new_boefjes_cache[organisation_id].values()
        self.organisations_new_boefjes_cache[organisation_id] = {}
        return new_boefjes
