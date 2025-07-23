from openkat.exceptions import ServiceException


class KATalogusException(ServiceException):
    def __init__(self, *args):
        super().__init__("KATalogus", *args)


class KATalogusDownException(KATalogusException):
    pass


class KATalogusUnhealthyException(KATalogusException):
    pass
