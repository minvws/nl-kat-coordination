from datetime import datetime
from typing import Any

from octopoes.models.transaction import TransactionRecord
from octopoes.repositories.repository import Repository
from octopoes.xtdb.client import XTDBSession


class NibbleRepository(Repository):
    def get(self, nibble: str, valid_time: datetime) -> dict[str, Any]:
        raise NotImplementedError

    def get_all(self, valid_time: datetime) -> list[dict[str, Any]]:
        raise NotImplementedError

    def put(self, ini: dict[str, Any], valid_time: datetime):
        raise NotImplementedError

    def put_many(self, inis: list[dict[str, Any]], valid_time: datetime):
        raise NotImplementedError

    def history(self, nibble: str, with_docs: bool = False) -> list[TransactionRecord]:
        raise NotImplementedError


class XTDBNibbleRepository(NibbleRepository):
    def __init__(self, session: XTDBSession):
        self.session = session

    @classmethod
    def _xtid(cls, nibble: str) -> str:
        return f"NibbleIni|{nibble}"

    @classmethod
    def _inify(cls, ini: dict[str, Any]) -> dict[str, Any]:
        ini["type"] = "NibbleIni"
        ini["xt/id"] = cls._xtid(ini["id"])
        return ini

    @classmethod
    def _deinify(cls, ini: dict[str, Any]) -> dict[str, Any]:
        ini.pop("type", None)
        ini.pop("xt/id", None)
        return ini

    def get(self, nibble: str, valid_time: datetime) -> dict[str, Any]:
        return self._deinify(self.session.client.get_entity(self._xtid(nibble), valid_time))

    def get_all(self, valid_time: datetime) -> list[dict[str, Any]]:
        result = self.session.client.query(
            '{:query {:find [(pull ?var [*])] :where [[?var :type "NibbleIni"]]}}', valid_time
        )
        return [self._deinify(item[0]) for item in result]

    def put(self, ini: dict[str, Any], valid_time: datetime):
        self.session.put(self._inify(ini), valid_time)
        self.commit()

    def put_many(self, inis: list[dict[str, Any]], valid_time: datetime):
        for ini in inis:
            self.session.put(self._inify(ini), valid_time)
        self.commit()

    def history(self, nibble: str, with_docs: bool = False) -> list[TransactionRecord]:
        return self.session.client.get_entity_history(self._xtid(nibble), with_docs=with_docs)

    def status(self):
        return self.session.client.status()

    def commit(self):
        self.session.commit()
