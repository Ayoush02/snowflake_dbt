"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Disallow hardcoded environment warehouse names in dynamic tables and tasks.
Use Jinja {{ warehouses.ELT }} instead of WH_DEV_ELT_XS / WH_PROD_ELT_XS.
"""

import re
from pathlib import Path


class HardcodedWarehouseRefValidator:

    WAREHOUSE_OBJECT_TYPES = ("dynamic_tables", "tasks")

    HARDCODED_WAREHOUSE_PATTERN = re.compile(
        r"\bWH_(?:DEV|PROD)_[A-Z0-9_]+\b",
        re.IGNORECASE,
    )

    def __init__(self, logger, root_folder="snowflake"):
        self.logger = logger
        self.root_folder = Path(root_folder)

    def validate(self):

        self.logger.info(
            "Validating dynamic_tables/tasks for hardcoded warehouse names..."
        )

        violations = []

        for object_type in self.WAREHOUSE_OBJECT_TYPES:
            object_root = self.root_folder / object_type

            if not object_root.is_dir():
                continue

            for sql_file in object_root.rglob("*.sql"):
                content = sql_file.read_text(encoding="utf-8")

                if self.HARDCODED_WAREHOUSE_PATTERN.search(content):
                    violations.append(str(sql_file))

        if violations:
            self.logger.error(
                "Hardcoded WH_DEV_/WH_PROD_ warehouse names found in "
                "dynamic_tables or tasks. Use Jinja {{ warehouses.ELT }} etc."
            )

            for file_path in violations:
                self.logger.error(file_path)

            raise ValueError("Hardcoded warehouse reference validation failed.")

        self.logger.info(
            "Dynamic tables/tasks warehouse reference validation successful."
        )
