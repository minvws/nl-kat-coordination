from queue import Full


class QueueEmptyError(Exception):
    pass


class NotAllowedError(Exception):
    pass


class InvalidPrioritizedItemError(ValueError):
    pass


class QueueFullError(Full):
    pass
