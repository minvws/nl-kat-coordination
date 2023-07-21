from enum import Enum
from typing import Dict, List, Set, Tuple, Union


class Channel(Enum):
    WARNING = "warning/boefje"
    INFO = "info/boefje"
    DEBUG = "debug/boefje"


class BoefjeOutput:
    def __init__(self) -> None:
        self.channels: Dict[Channel, List[str]] = {}
        for channel in Channel:
            self.channels[channel] = [f"BEGIN LOG - {channel}"]

    def writeln(self, channel: Channel, line: str) -> None:
        self.channels[channel].append(line)

    def format(
        self, boefje_mimetype: Set[str], boefje_result: Union[bytes, str]
    ) -> List[Tuple[Set[str], Union[bytes, str]]]:
        return_list: List[Tuple[Set[str], Union[bytes, str]]] = [(boefje_mimetype, boefje_result)]

        for channel in self.channels:
            if len(self.channels[channel]) > 1:
                return_list.append(({channel.value}, "\n".join(self.channels[channel])))

        return return_list
