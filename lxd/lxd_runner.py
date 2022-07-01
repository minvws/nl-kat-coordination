import json
import logging
from datetime import datetime, timezone
from typing import Union, Optional, Tuple, Dict, List

import pydantic
import pylxd
import pylxd.exceptions
import pylxd.models
import requests

from boefjes.models import RawData
from config import settings
from job import BoefjeMeta
from katalogus.models import PluginType
from runner import BoefjeJobRunner

logger = logging.getLogger(__name__)

_DEFAULT_LXD_CONFIG = {
    "name": None,
    "source": {"type": "image", "alias": None},
    "devices": {
        "eth0": {
            "name": "eth0",
            "nictype": "bridged",
            "parent": "lxdbr0",
            "type": "nic",
            "host_name": "boefje_nic0",
        }
    },
    "profiles": ["default"],
}


def get_simplestreams_endpoint(organisation: str, repository: str) -> str:
    simplestreams_endpoint = requests.get(
        f"{settings.katalogus_api}/v1/organisations/{organisation}/repositories/{repository}"
    ).json()["base_url"]

    return simplestreams_endpoint


def get_environment_settings(organisation: str, keys: List[str]) -> Dict[str, str]:
    environment = requests.get(
        f"{settings.katalogus_api}/v1/organisations/{organisation}/settings"
    ).json()

    return {k: v for k, v in environment.items() if k in keys}


def get_plugin(
    organisation: str, repository: str, plugin_id: str, version: str
) -> PluginType:
    res = requests.get(
        f"{settings.katalogus_api}/v1/organisations/{organisation}/repositories/{repository}/plugins/{plugin_id}:{version}"
    )

    return pydantic.parse_raw_as(PluginType, res.content)


class LXDBoefjeJobRunner(BoefjeJobRunner):
    def __init__(self, boefje_meta: BoefjeMeta, plugin: PluginType):
        self.boefje_meta = boefje_meta
        self.raw: Optional[Union[str, bytes]] = None
        self.plugin = plugin

    def run(self) -> Tuple[BoefjeMeta, RawData]:
        self.boefje_meta.started_at = datetime.now(timezone.utc)
        self.boefje_meta, raw = self._execute_boefje_plugin(
            self.boefje_meta, self.plugin
        )
        self.boefje_meta.ended_at = datetime.now(timezone.utc)

        return self.boefje_meta, RawData(data=raw, mime_types={self.plugin.id})

    def _execute_boefje_plugin(self, meta: BoefjeMeta, plugin: PluginType) -> str:
        client = self._create_lxd_client(settings.lxd_endpoint, settings.lxd_password)
        repository, plugin_id = meta.boefje.id.split("/")
        alias = f"{plugin_id}/{meta.boefje.version}"

        payload = {
            "input": meta.arguments["input"],
            "input_ooi": meta.input_ooi,
            "type": "boefje",
        }

        environment = get_environment_settings(
            meta.organization, plugin.environment_keys
        )

        simplestreams_endpoint = get_simplestreams_endpoint(
            meta.organization, repository
        )

        config = _DEFAULT_LXD_CONFIG.copy()
        instance_name = plugin_id + "-" + meta.id.split("-", 1)[0]
        config["name"] = instance_name
        config["source"]["alias"] = alias
        config["source"]["server"] = simplestreams_endpoint
        config["source"]["protocol"] = "simplestreams"
        config["source"]["mode"] = "pull"

        try:
            try:
                logger.info("Getting instance")
                instance: pylxd.models.Instance = client.instances.get(instance_name)

                if instance.status not in ["Stopped", "Stopping"]:
                    instance.stop(wait=True, force=True)
            except pylxd.exceptions.NotFound:
                logger.info('Instance not found, creating "%s"...', instance_name)
                logger.debug("Instance config: %s", config)
                instance = client.instances.create(config, wait=True)
                logger.info('Created "%s"', instance.name)
                instance.start(wait=True)

            logger.info("Starting runner with payload: %s", payload)
            exit_code, stdout, stderr = instance.execute(
                ["python3", "-m", "runner"],
                stdin_payload=json.dumps(payload),
                environment=environment,
                cwd="/plugin",
            )

            logger.debug("exit_code: %d", exit_code)
            logger.debug("stdout: %s", stdout)
            logger.debug("stderr: %s", stderr)

            if exit_code != 0:
                logger.error(
                    "Plugin execution failed. Exit code: %d, stderr: %s",
                    exit_code,
                    stderr,
                )
                raise RuntimeError(f"Plugin execution failed ({exit_code}): {stderr}")

            logger.debug("Result: %s", stdout)

            result = json.loads(stdout)["success"]["output"].encode()

            logger.info("Execution finished with result: %s", result)

            instance.stop(wait=True)

            return result

        except Exception as ex:
            logger.exception("Error while executing plugin")
            raise ex

        finally:
            if client.instances.exists(instance_name):
                instance = client.instances.get(instance_name)
                instance.delete()

    @staticmethod
    def _create_lxd_client(endpoint: str, password: Optional[str]) -> pylxd.Client:
        client = pylxd.Client(endpoint, cert=None, verify=False)

        if password is not None:
            client.authenticate(password)

        return client
