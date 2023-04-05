"""Keiko settings module."""
from pathlib import Path

from pydantic import BaseSettings, Field, DirectoryPath, FilePath


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    debug: bool = Field(False, description="Enable debug mode")
    log_cfg: FilePath = Field("logging.json", description="Path to the logging configuration file")
    templates_folder: DirectoryPath = Field("templates", description="Folder containing the templates")
    glossaries_folder: DirectoryPath = Field("glossaries", description="Folder containing the glossaries")
    assets_folder: DirectoryPath = Field("assets", description="Folder containing the assets")
    reports_folder: Path = Field("/reports", description="Output folder containing the reports")

    class Config:
        env_prefix = "KEIKO_"
