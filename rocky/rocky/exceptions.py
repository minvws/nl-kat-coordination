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


class OctopoesException(RockyError):
    pass


class OctopoesDownException(OctopoesException):
    def __init__(self):
        super().__init__("Octopoes is down")


class OctopoesUnhealthyException(OctopoesException):
    def __init__(self):
        super().__init__("Octopoes is not healthy")
