import fastapi
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from scheduler import storage


def exception_handler(request: fastapi.Request, exc: Exception):
    status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR
    detail=f"An internal error occurred: {exc}"

    if isinstance(exc, storage.filters.errors.FilterError):
        status_code=fastapi.status.HTTP_400_BAD_REQUEST
        detail=f"Invalid filter(s): {exc}"
    elif isinstance(exc, storage.errors.StorageError):
        status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR
        detail=f"A database error occurred: {exc}"
    elif isinstance(exc, ValidationError):
        status_code=fastapi.status.HTTP_400_BAD_REQUEST
        detail=f"Validation error occurred: {exc}"
    elif isinstance(exc, fastapi.HTTPException):
        status_code=exc.status_code
        detail=exc.detail

    return JSONResponse(
        status_code=status_code,
        content={"detail": detail})
    ) 
