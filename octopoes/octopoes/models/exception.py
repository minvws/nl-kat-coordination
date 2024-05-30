from __future__ import annotations


class ObjectNotFoundException(Exception):
    def __init__(self, value: str):
        self.value = value


class TypeNotFound(ValueError):
    pass
