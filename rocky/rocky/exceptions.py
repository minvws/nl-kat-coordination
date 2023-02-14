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
