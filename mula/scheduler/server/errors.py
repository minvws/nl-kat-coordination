import fastapi
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from scheduler import storage


def exception_handler(request: fastapi.Request, exc: Exception):
    if isinstance(exc, storage.filters.errors.FilterError):
        return JSONResponse(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST, content={"detail": f"Invalid filter(s): {exc}"}
        )
    elif isinstance(exc, storage.errors.StorageError):
        return JSONResponse(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"A database error occurred: {exc}"},
        )
    elif isinstance(exc, ValidationError):
        return JSONResponse(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST, content={"detail": f"Validation error occurred: {exc}"}
        )
    elif isinstance(exc, fastapi.HTTPException):
        return fastapi.responses.JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    else:
        return JSONResponse(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An internal error occurred: {exc}"},
        )
