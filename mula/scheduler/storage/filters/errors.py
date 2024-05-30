class FilterError(Exception):
    pass


class UnsupportedTypeError(FilterError):
    pass


class MismatchedTypeError(FilterError):
    pass


class ArgumentError(FilterError):
    pass
