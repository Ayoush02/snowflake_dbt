"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Central logging utility used across the deployment framework.
"""

import logging
import os
from pathlib import Path


class Logger:

    def __init__(self, log_level="INFO"):

        log_directory = Path("logs")
        log_directory.mkdir(exist_ok=True)

        log_file = log_directory / "deployment.log"

        self.logger = logging.getLogger("SnowflakeDeployment")

        self.logger.setLevel(getattr(logging, log_level.upper()))

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        if not self.logger.handlers:

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def info(self, message):

        self.logger.info(message)

    def warning(self, message):

        self.logger.warning(message)

    def error(self, message):

        self.logger.error(message)

    def critical(self, message):

        self.logger.critical(message)

    def exception(self, message):

        self.logger.exception(message)