from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import structlog
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import InvalidTokenError
from pydantic import BaseModel
from starlette import status

from bytes.config import get_settings

logger = structlog.get_logger(__name__)

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: str


def get_access_token(form_data: OAuth2PasswordRequestForm) -> tuple[str, datetime]:
    settings = get_settings()
    system_username = settings.username

    if len(settings.password) > 72:
        logger.warning("Password length exceeds bcrypt limit of 72 characters; truncating for hashing.")

    # bcrypt works with bytes and truncates at 72 bytes; apply same truncation explicitly
    system_pw_bytes = settings.password[:72].encode("utf-8")
    hashed_password = bcrypt.hashpw(system_pw_bytes, bcrypt.gensalt())

    # truncate incoming password the same way before verification
    incoming_pw_bytes = form_data.password[:72].encode("utf-8")
    authenticated = form_data.username == system_username and bcrypt.checkpw(incoming_pw_bytes, hashed_password)

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _create_access_token(form_data, settings.secret, settings.access_token_expire_minutes)


def authenticate_token(token: str = Depends(oauth2_scheme)) -> str:
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise credentials_exception

        return str(username)
    except InvalidTokenError as error:
        raise credentials_exception from error


def _create_access_token(
    form_data: OAuth2PasswordRequestForm, secret: str, access_token_expire_minutes: float
) -> tuple[str, datetime]:
    expire_time = _get_expire_time(access_token_expire_minutes)
    data = {"sub": form_data.username, "exp": expire_time}

    access_token = jwt.encode(data.copy(), secret, algorithm=ALGORITHM)

    return access_token, expire_time


def _get_expire_time(access_token_expire_minutes: float) -> datetime:
    access_token_expires = timedelta(minutes=access_token_expire_minutes)

    return datetime.now(timezone.utc) + access_token_expires
