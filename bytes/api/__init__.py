import logging.config

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from bytes.api import root
from bytes.api.root import validation_exception_handler
from bytes.api.v2 import router as router_v2


from bytes.config import get_settings

logging.config.fileConfig(get_settings().log_cfg, disable_existing_loggers=False)

app = FastAPI()

app.include_router(root.router)
app.include_router(router_v2.router, prefix="/bytes")
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
