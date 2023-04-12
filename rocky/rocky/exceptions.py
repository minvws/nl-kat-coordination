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
    def __init__(self, service: str, *args):
        super().__init__(*args)
        self.service = service


class OctopoesException(ServiceException):
    def __init__(self, *args):
        super().__init__("Octopoes", *args)


class OctopoesDownException(OctopoesException):
    pass


class OctopoesUnhealthyException(OctopoesException):
    pass
