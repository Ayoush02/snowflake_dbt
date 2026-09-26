"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Validate access_roles configuration for grant scripts.
"""

from pathlib import Path

from deployment.core.jinja_vars import (
    build_access_role,
    get_layer_codes,
    get_schema_codes,
    resolve_schema_code,
)


class GrantRolesValidator:

    REQUIRED_LAYERS = ("RAW", "TRANSFORM", "CONSUMPTION")

    def __init__(self, logger, deployment_config, root_folder="snowflake"):
        self.logger = logger
        self.deployment_config = deployment_config
        self.grants_root = Path(root_folder) / "grants"

    def validate(self):

        if not self._has_grant_scripts():
            self.logger.info(
                "Skipping access role validation (no grant SQL scripts found)."
            )
            return

        access_roles = self.deployment_config.get("access_roles")

        if not access_roles:
            raise ValueError(
                "Grant SQL scripts exist but access_roles is missing from "
                "deployment/config/deployment.yml."
            )

        layer_codes = get_layer_codes(self.deployment_config)
        schema_codes = get_schema_codes(self.deployment_config)

        missing_layers = [
            layer
            for layer in self.REQUIRED_LAYERS
            if layer not in layer_codes
        ]

        if missing_layers:
            raise ValueError(
                "access_roles.layer_codes must define: "
                + ", ".join(missing_layers)
            )

        default_privilege = str(
            access_roles.get("default_privilege", "RW")
        ).upper()

        if default_privilege not in {"ALL", "RO", "RW"}:
            raise ValueError(
                "access_roles.default_privilege must be one of: ALL, RO, RW"
            )

        grant_targets = self._discover_grant_targets()
        unknown_schemas = []

        for layer, schema in grant_targets:
            if resolve_schema_code(schema, schema_codes) == schema.upper().replace(
                "_", ""
            ) and schema.upper() not in schema_codes:
                unknown_schemas.append(f"{layer}/{schema}")

            for environment in ("DEV", "PROD"):
                build_access_role(
                    environment,
                    layer,
                    schema,
                    default_privilege,
                    self.deployment_config,
                )

        if unknown_schemas:
            self.logger.warning(
                "Grant targets use schema folders without explicit schema_codes "
                "mapping (falling back to folder name without underscores): "
                + ", ".join(sorted(set(unknown_schemas)))
            )

        self.logger.info("Access role configuration validation successful.")

    def _discover_grant_targets(self) -> set[tuple[str, str]]:
        targets: set[tuple[str, str]] = set()

        if not self.grants_root.is_dir():
            return targets

        for layer_path in self.grants_root.iterdir():
            if not layer_path.is_dir():
                continue

            for schema_path in layer_path.iterdir():
                if schema_path.is_dir() and any(schema_path.rglob("*.sql")):
                    targets.add((layer_path.name.upper(), schema_path.name.upper()))

        return targets

    def _has_grant_scripts(self) -> bool:
        if not self.grants_root.is_dir():
            return False

        return any(self.grants_root.rglob("*.sql"))
