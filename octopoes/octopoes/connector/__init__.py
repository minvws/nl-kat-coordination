# Keep for backwards compatibility
from octopoes.models.exception import ObjectNotFoundException


class ConnectorException(Exception):
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value


class RemoteException(ConnectorException):
    pass
