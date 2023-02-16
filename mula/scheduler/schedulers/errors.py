class TaskNotAllowedToRunException(Exception):
    pass


class TaskAlreadyRunningError(Exception):
    pass


class TaskGracePeriodNotPassedError(Exception):
    pass


class TaskAlreadyOnQueueuError(Exception):
    pass


class OOINotFoundError(Exception):
    pass


class PluginDisabledError(Exception):
    pass


class PluginNotFoundError(Exception):
    pass
