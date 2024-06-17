import json
from datetime import datetime

from pydantic import JsonValue, TypeAdapter

from bits.definitions import BitDefinition
from bits.runner import BitRunner
from octopoes.models import OOI


class BitCache:
    def __init__(self):
        self.bit_cache: dict[BitDefinition, dict[str, tuple[list[OOI], datetime]]] = {}

    def _purge(self, bit: BitDefinition) -> None:
        now = datetime.now()
        map(
            self.bit_cache[bit].pop,
            [key for key, data in self.bit_cache[bit].items() if now - data[1] <= bit.cache_lifetime],
        )

    def _bit_cache_key(self, source: OOI, parameters: list[OOI], config: dict[str, JsonValue]) -> str:
        try:
            serialized_ooi = str(TypeAdapter(list[OOI]).dump_json(parameters))
            return source.model_dump_json() + serialized_ooi + json.dumps(config)
        except Exception:
            return str(datetime.now())

    def get_bit(
        self, bit: BitDefinition, source: OOI, parameters: list[OOI], config: dict[str, JsonValue]
    ) -> list[OOI]:
        key = self._bit_cache_key(source, parameters, config)
        if bit not in self.bit_cache:
            data = BitRunner(bit).run(source, parameters, config=config)
            self.bit_cache[bit] = {key: (data, datetime.now())}
        else:
            self._purge(bit)
            if key not in self.bit_cache[bit]:
                data = BitRunner(bit).run(source, parameters, config=config)
                self.bit_cache[bit][key] = (data, datetime.now())
        return self.bit_cache[bit][key][0]


BIT_CACHE: BitCache = BitCache()
