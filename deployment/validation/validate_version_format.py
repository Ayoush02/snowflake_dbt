"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Validate SchemaChange File Naming Convention
"""

import re
from pathlib import Path


class VersionFormatValidator:

    def __init__(self, logger, root_folder="snowflake"):

        self.logger = logger
        self.root_folder = Path(root_folder)

        self.version_pattern = re.compile(
            r"^V\d+\.\d+\.\d+__.+\.sql$",
            re.IGNORECASE,
        )

        self.placeholder_pattern = re.compile(
            r"^V__.+\.sql$",
            re.IGNORECASE,
        )

        self.repeatable_pattern = re.compile(
            r"^R__.+\.sql$",
            re.IGNORECASE,
        )

    def validate(self):

        self.logger.info("Validating SchemaChange File Naming...")

        invalid_files = []

        for sql_file in self.root_folder.rglob("*.sql"):
            filename = sql_file.name

            if self.version_pattern.match(filename):
                continue

            if self.placeholder_pattern.match(filename):
                continue

            if self.repeatable_pattern.match(filename):
                continue

            invalid_files.append(str(sql_file))

        if invalid_files:
            self.logger.error("Invalid Migration File Names Found.")

            for file_path in invalid_files:
                self.logger.error(file_path)

            raise ValueError("Migration File Validation Failed.")

        self.logger.info("Migration File Validation Successful.")
