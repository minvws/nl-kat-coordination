"""Keiko settings module."""
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, DirectoryPath, Field, FilePath


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    debug: bool = Field(
        False, description="Enable debug mode"
    )  # Follow-up ticket to make debug mode the same for all modules?
    log_cfg: FilePath = Field(
        "logging.json", description="Path to the logging configuration file"
    )  # Follow-up ticket to make logging the same for all modules?
    templates_folder: DirectoryPath = Field("templates", description="Folder containing the templates")
    glossaries_folder: DirectoryPath = Field("glossaries", description="Folder containing the glossaries")
    assets_folder: DirectoryPath = Field("assets", description="Folder containing the assets")
    reports_folder: Path = Field("/reports", description="Output folder containing the reports")
    # `description` and pydantic typing would be nice to have in all module settings/config.py files
    span_export_grpc_endpoint: Optional[str] = Field(None, env="SPAN_EXPORT_GRPC_ENDPOINT")

    class Config:
        env_prefix = "KEIKO_"  # Nice. Maybe have this snippet in all module settings/config.py files?
