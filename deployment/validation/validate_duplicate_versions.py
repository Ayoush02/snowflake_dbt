"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Validate duplicate versioned migration numbers.
"""

import re
from collections import defaultdict
from pathlib import Path


class DuplicateVersionValidator:

    VERSION_PATTERN = re.compile(
        r"^V(?P<version>\d+\.\d+\.\d+)__",
        re.IGNORECASE,
    )

    def __init__(self, logger, root_folder="snowflake"):
        self.logger = logger
        self.root_folder = Path(root_folder)

    def validate(self):

        self.logger.info("Validating duplicate migration versions...")

        version_map = defaultdict(list)

        for sql_file in self.root_folder.rglob("*.sql"):
            match = self.VERSION_PATTERN.match(sql_file.name)

            if not match:
                continue

            version = match.group("version")
            version_map[version].append(str(sql_file))

        duplicates = {
            version: files
            for version, files in version_map.items()
            if len(files) > 1
        }

        if duplicates:
            self.logger.error("Duplicate versioned migration numbers found.")

            for version, files in sorted(duplicates.items()):
                self.logger.error(f"Version {version}:")
                for file_path in files:
                    self.logger.error(f"  - {file_path}")

            raise ValueError("Duplicate migration version validation failed.")

        self.logger.info("Duplicate migration version validation successful.")
