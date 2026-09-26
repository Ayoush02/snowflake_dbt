"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Validate database/schema folder names used in the repository structure.
"""

import re
from pathlib import Path

from deployment.core.schema_discovery import SchemaDiscovery


class SchemaPathValidator:

    IDENTIFIER_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

    def __init__(self, logger, root_folder, deployment_order):
        self.logger = logger
        self.discovery = SchemaDiscovery(root_folder, deployment_order)

    def validate(self):

        self.logger.info("Validating database/schema folder names...")

        invalid_names = []

        root = Path(self.discovery.root_folder)

        for object_type in self.discovery.deployment_order:
            object_type_path = root / object_type

            if not object_type_path.is_dir():
                continue

            if object_type == "snowpark":
                self._validate_snowpark_paths(object_type_path, invalid_names)
                continue

            if object_type == "streamlit_apps":
                self._validate_streamlit_apps_paths(object_type_path, invalid_names)
                continue

            if object_type not in SchemaDiscovery.OBJECT_TYPES_WITH_SCHEMA:
                continue

            for database_path in object_type_path.iterdir():
                if database_path.is_dir():
                    self._validate_name(database_path.name, database_path, invalid_names)

                for schema_path in database_path.iterdir() if database_path.is_dir() else []:
                    if schema_path.is_dir():
                        self._validate_name(schema_path.name, schema_path, invalid_names)

        if invalid_names:
            self.logger.error("Invalid database/schema folder names found.")

            for name in invalid_names:
                self.logger.error(name)

            raise ValueError("Schema path validation failed.")

        targets = self.discovery.discover_targets()

        if not targets:
            self.logger.warning(
                "No database/schema targets discovered yet. "
                "Add SQL migrations under snowflake/<object>/<database>/<schema>/."
            )
        else:
            self.logger.info(
                f"Schema path validation successful for {len(targets)} target(s)."
            )

    def _validate_snowpark_paths(self, snowpark_root, invalid_names):

        for database_path in snowpark_root.iterdir():
            if not database_path.is_dir():
                continue

            self._validate_name(database_path.name, database_path, invalid_names)

            for schema_path in database_path.iterdir():
                if not schema_path.is_dir():
                    continue

                self._validate_name(schema_path.name, schema_path, invalid_names)

                for procedure_path in schema_path.iterdir():
                    if procedure_path.is_dir():
                        self._validate_name(
                            procedure_path.name,
                            procedure_path,
                            invalid_names,
                        )

    def _validate_streamlit_apps_paths(self, streamlit_apps_root, invalid_names):

        for database_path in streamlit_apps_root.iterdir():
            if not database_path.is_dir():
                continue

            self._validate_name(database_path.name, database_path, invalid_names)

            for schema_path in database_path.iterdir():
                if not schema_path.is_dir():
                    continue

                self._validate_name(schema_path.name, schema_path, invalid_names)

                for app_path in schema_path.iterdir():
                    if app_path.is_dir():
                        self._validate_name(
                            app_path.name,
                            app_path,
                            invalid_names,
                        )

    def _validate_name(self, name, path, invalid_names):

        normalized = name.upper()

        if not self.IDENTIFIER_PATTERN.match(normalized):
            invalid_names.append(
                f"{path}: '{name}' is not a valid Snowflake identifier."
            )
