import functools

import httpx
import pydantic


class ExternalServiceError(Exception):
    pass


def exception_handler(func):
    @functools.wraps(func)
    def inner_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except httpx.ConnectError as exc:
            raise ExternalServiceError("External service is not available.") from exc
        except pydantic.ValidationError:
            ExternalServiceError("Validation error occurred.")
        except Exception as exc:
            raise ExternalServiceError("External service returned an error.") from exc

    return inner_function
