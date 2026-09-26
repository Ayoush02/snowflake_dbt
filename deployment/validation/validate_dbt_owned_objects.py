"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Tables and views are owned by dbt, not SchemaChange.
"""

from pathlib import Path


class DbtOwnedObjectsValidator:

    SCHEMACHANGE_FORBIDDEN = ("tables", "views")

    def __init__(self, logger, root_folder="snowflake"):
        self.logger = logger
        self.root_folder = Path(root_folder)

    def validate(self):
        self.logger.info(
            "Validating that tables and views are created by dbt only..."
        )

        violations = []

        for object_type in self.SCHEMACHANGE_FORBIDDEN:
            object_root = self.root_folder / object_type

            if not object_root.exists():
                continue

            sql_files = sorted(object_root.rglob("*.sql"))
            if sql_files:
                violations.extend(str(path) for path in sql_files)
            else:
                violations.append(
                    f"{object_root} (remove this folder; tables/views belong in dbt/)"
                )

        if violations:
            self.logger.error(
                "Tables and views must be created by dbt models, not SchemaChange. "
                "Remove snowflake/tables and snowflake/views; put models under dbt/models/."
            )
            for path in violations:
                self.logger.error(path)
            raise ValueError("dbt-owned object validation failed.")

        self.logger.info(
            "Tables/views SchemaChange exclusion validation successful."
        )
