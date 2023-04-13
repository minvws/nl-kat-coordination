import logging.config

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from bytes.api.root import router as root_router
from bytes.api.root import validation_exception_handler
from bytes.api.router import router


from bytes.config import get_settings

logging.config.fileConfig(get_settings().log_cfg, disable_existing_loggers=False)

app = FastAPI()

app.include_router(root_router)
app.include_router(router, prefix="/bytes")
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
