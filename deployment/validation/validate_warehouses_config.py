"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Validate warehouses configuration for dynamic table and task scripts.
"""

from pathlib import Path

from deployment.core.jinja_vars import build_warehouses


class WarehousesConfigValidator:

    WAREHOUSE_OBJECT_TYPES = ("dynamic_tables", "tasks")
    REQUIRED_ENVIRONMENTS = ("DEV", "PROD")

    def __init__(self, logger, deployment_config, root_folder="snowflake"):
        self.logger = logger
        self.deployment_config = deployment_config
        self.root_folder = Path(root_folder)

    def validate(self):

        if not self._has_warehouse_object_scripts():
            self.logger.info(
                "Skipping warehouse config validation "
                "(no dynamic_tables or tasks SQL scripts found)."
            )
            return

        warehouses = self.deployment_config.get("warehouses")

        if not warehouses:
            raise ValueError(
                "Dynamic table or task SQL scripts exist but warehouses is "
                "missing from deployment/config/deployment.yml."
            )

        for name, env_map in warehouses.items():
            if not isinstance(env_map, dict):
                raise ValueError(
                    f"warehouses.{name} must map DEV and PROD warehouse names."
                )

            for environment in self.REQUIRED_ENVIRONMENTS:
                warehouse_name = env_map.get(environment)

                if not warehouse_name:
                    raise ValueError(
                        f"warehouses.{name}.{environment} must be configured."
                    )

        for environment in self.REQUIRED_ENVIRONMENTS:
            build_warehouses(environment, self.deployment_config)

        self.logger.info("Warehouse configuration validation successful.")

    def _has_warehouse_object_scripts(self) -> bool:
        for object_type in self.WAREHOUSE_OBJECT_TYPES:
            object_root = self.root_folder / object_type

            if object_root.is_dir() and any(object_root.rglob("*.sql")):
                return True

        return False
