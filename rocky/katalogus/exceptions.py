from rocky.exceptions import RockyError


class KatalogusException(RockyError):
    pass


class KatalogusDownException(KatalogusException):
    def __init__(self):
        super().__init__("The Katalogus is down")


class KatalogusUnhealthyException(KatalogusException):
    def __init__(self):
        super().__init__("The Katalogus is not healthy")
