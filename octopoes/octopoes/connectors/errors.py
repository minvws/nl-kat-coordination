"""Connector errors."""

import functools
from typing import Callable, Any, TypeVar, cast

import pydantic


class ValidationError(Exception):
    """Validation error."""


FuncT = TypeVar("FuncT", bound=Callable[..., Any])


def exception_handler(func: FuncT) -> FuncT:
    """Wrap function in exception handler."""

    @functools.wraps(func)
    def inner_function(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except pydantic.error_wrappers.ValidationError as exc:
            raise ValidationError("Not able to parse response from external service.") from exc

    return cast(FuncT, inner_function)
