import functools

import fastapi
import pydantic

from scheduler import storage


def exception_handler(func):
    @functools.wraps(func)
    def inner_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except storage.filters.errors.FilterError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail=f"Invalid filter(s): {exc}]"
            ) from exc
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"A database error occurred: {exc}"
            ) from exc
        except pydantic.ValidationError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail=f"Validation error occurred: {exc}"
            ) from exc
        except fastapi.HTTPException as exc:
            raise exc
        except Exception as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {exc}"
            ) from exc

    return inner_function
