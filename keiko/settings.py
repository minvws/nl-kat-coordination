"""Keiko settings module."""

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    debug: bool = Field(False, env="KEIKO_DEBUG")
    log_cfg: str = Field(
        "logging.json",
        env="KEIKO_LOG_CFG",
    )

    templates_folder: str = Field("templates", env="KEIKO_TEMPLATES_FOLDER")
    glossaries_folder: str = Field("glossaries", env="KEIKO_GLOSSARIES_FOLDER")
    reports_folder: str = Field("reports", env="KEIKO_REPORTS_FOLDER")
    assets_folder: str = Field("assets", env="KEIKO_ASSETS_FOLDER")
