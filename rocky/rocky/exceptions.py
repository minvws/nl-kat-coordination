class RockyError(Exception):
    pass


class IndemnificationNotPresentException(Exception):
    pass


class ClearanceLevelTooLowException(Exception):
    pass


class AcknowledgedClearanceLevelTooLowException(ClearanceLevelTooLowException):
    pass


class TrustedClearanceLevelTooLowException(ClearanceLevelTooLowException):
    pass


class ServiceException(RockyError):
    """Base exception representing an issue with an (external) service"""

    def __init__(self, service_name: str, *args):
        super().__init__(*args)
        self.service_name = service_name


class OctopoesException(ServiceException):
    def __init__(self, *args):
        super().__init__("Octopoes", *args)


class OctopoesDownException(OctopoesException):
    pass


class OctopoesUnhealthyException(OctopoesException):
    pass
