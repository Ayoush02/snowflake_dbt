"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Disallow hardcoded environment database names in views and dynamic tables.
Use Jinja {{ databases.RAW }} instead of DEV_RAW / PROD_RAW.
"""

import re
from pathlib import Path


class HardcodedDatabaseRefValidator:

    CROSS_LAYER_OBJECT_TYPES = ("views", "dynamic_tables")

    HARDCODED_DATABASE_PATTERN = re.compile(
        r"\b(?:DEV|PROD)_(?:RAW|TRANSFORM|CONSUMPTION|UTILS)\b",
        re.IGNORECASE,
    )

    def __init__(self, logger, root_folder="snowflake"):
        self.logger = logger
        self.root_folder = Path(root_folder)

    def validate(self):

        self.logger.info(
            "Validating views/dynamic_tables for hardcoded database names..."
        )

        violations = []

        for object_type in self.CROSS_LAYER_OBJECT_TYPES:
            object_root = self.root_folder / object_type

            if not object_root.is_dir():
                continue

            for sql_file in object_root.rglob("*.sql"):
                content = sql_file.read_text(encoding="utf-8")

                if self.HARDCODED_DATABASE_PATTERN.search(content):
                    violations.append(str(sql_file))

        if violations:
            self.logger.error(
                "Hardcoded DEV_/PROD_ database names found in views or "
                "dynamic_tables. Use Jinja {{ databases.RAW }} etc."
            )

            for file_path in violations:
                self.logger.error(file_path)

            raise ValueError("Hardcoded database reference validation failed.")

        self.logger.info(
            "Views/dynamic_tables database reference validation successful."
        )
