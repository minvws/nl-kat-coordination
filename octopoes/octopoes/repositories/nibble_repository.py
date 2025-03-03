from datetime import datetime
from typing import Any

from octopoes.models.transaction import TransactionRecord
from octopoes.repositories.repository import Repository
from octopoes.xtdb.client import XTDBSession

NibbleINI = dict[str, Any]


class NibbleRepository(Repository):
    def get(self, nibble_id: str, valid_time: datetime) -> NibbleINI:
        raise NotImplementedError

    def get_all(self, valid_time: datetime) -> list[NibbleINI]:
        raise NotImplementedError

    def put(self, ini: NibbleINI, valid_time: datetime):
        raise NotImplementedError

    def put_many(self, inis: list[NibbleINI], valid_time: datetime):
        raise NotImplementedError

    def history(self, nibble_id: str, with_docs: bool = False) -> list[TransactionRecord]:
        raise NotImplementedError


class XTDBNibbleRepository(NibbleRepository):
    def __init__(self, session: XTDBSession):
        self.session = session

    @classmethod
    def _xtid(cls, nibble_id: str) -> str:
        return f"NibbleINI|{nibble_id}"

    @classmethod
    def _serialize(cls, ini: NibbleINI) -> NibbleINI:
        ini["type"] = "NibbleINI"
        ini["xt/id"] = cls._xtid(ini["id"])
        return ini

    @classmethod
    def _deserialize(cls, ini: NibbleINI) -> NibbleINI:
        ini.pop("type", None)
        ini.pop("xt/id", None)
        return ini

    def get(self, nibble_id: str, valid_time: datetime) -> NibbleINI:
        return self._deserialize(self.session.client.get_entity(self._xtid(nibble_id), valid_time))

    def get_all(self, valid_time: datetime) -> list[NibbleINI]:
        result = self.session.client.query(
            '{:query {:find [(pull ?var [*])] :where [[?var :type "NibbleINI"]]}}', valid_time
        )
        return [self._deserialize(item[0]) for item in result]

    def put(self, ini: NibbleINI, valid_time: datetime):
        self.session.put(self._serialize(ini), valid_time)
        self.commit()

    def put_many(self, inis: list[NibbleINI], valid_time: datetime):
        for ini in inis:
            self.session.put(self._serialize(ini), valid_time)
        self.commit()

    def history(self, nibble_id: str, with_docs: bool = False) -> list[TransactionRecord]:
        return self.session.client.get_entity_history(self._xtid(nibble_id), with_docs=with_docs)

    def status(self):
        return self.session.client.status()

    def commit(self):
        self.session.commit()
