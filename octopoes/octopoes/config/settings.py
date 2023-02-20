"""Octopoes application settings."""

import os
from pathlib import Path

from pydantic import BaseSettings, AnyHttpUrl


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    debug: bool = False
    log_cfg: str = os.path.join(Path(__file__).parent.parent.parent, "logging.yml")

    # Server settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Application settings

    # External services settings
    katalogus_uri: AnyHttpUrl = "http://katalogus:8000/"  # type: ignore
    xtdb_uri: AnyHttpUrl = "http://xtdb:3000/_xtdb"  # type: ignore

    class Config:
        """Settings configuration."""

        env_prefix = "octopoes_"
