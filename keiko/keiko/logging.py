"""Keiko's Logging module."""

import json
import logging
from json import JSONDecodeError
from logging import config, getLogger

from keiko.settings import Settings


def setup_loggers(settings: Settings) -> None:
    """Load logging configuration."""
    logger = getLogger(__name__)
    try:
        with settings.log_cfg.open("rt", encoding="utf-8") as log_config:
            config.dictConfig(json.load(log_config))
            logger.info("Logging configuration loaded. [log_cfg=%s]", settings.log_cfg)
    except FileNotFoundError:
        logger.error("Logging configuration file not found. [log_cfg=%s]", settings.log_cfg)
    except JSONDecodeError:
        logger.error(
            "Logging configuration file is not a valid JSON file. [log_cfg=%s]",
            settings.log_cfg,
        )

    if settings.debug:
        # pylint fails on "Instance of 'RootLogger' has no 'loggerDict' member (no-member)"
        # pylint: disable=no-member

        loggers = [getLogger()]  # root logger
        loggers = loggers + [getLogger(name) for name in logging.root.manager.loggerDict]
        for logger in loggers:
            logger.setLevel(logging.DEBUG)
