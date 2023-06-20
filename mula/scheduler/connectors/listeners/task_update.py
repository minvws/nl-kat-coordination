from typing import Callable

from .listeners import Psql


class TaskUpdate(Psql):
    def __init__(self, engine, func: Callable):
        super().__init__(engine, "tasks_update", func)
