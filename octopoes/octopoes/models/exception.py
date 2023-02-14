class ObjectNotFoundException(Exception):
    def __init__(self, value: str):
        self.value = value
