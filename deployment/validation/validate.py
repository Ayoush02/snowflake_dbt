"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Master Validation Module
"""

from deployment.core.config_loader import load_yaml
from deployment.validation.validate_grant_roles import GrantRolesValidator
from deployment.validation.validate_hardcoded_database_refs import (
    HardcodedDatabaseRefValidator,
)
from deployment.validation.validate_hardcoded_warehouse_refs import (
    HardcodedWarehouseRefValidator,
)
from deployment.validation.validate_warehouses_config import (
    WarehousesConfigValidator,
)
from deployment.validation.validate_dbt_owned_objects import DbtOwnedObjectsValidator
from deployment.validation.validate_dbt_project import DbtProjectValidator
from deployment.validation.validate_duplicate_versions import DuplicateVersionValidator
from deployment.validation.validate_immutable_migrations import ImmutableMigrationValidator
from deployment.validation.validate_project_structure import ProjectStructureValidator
from deployment.validation.validate_schema_paths import SchemaPathValidator
from deployment.validation.validate_version_format import VersionFormatValidator


class Validator:

    def __init__(self, logger, base_ref=None):
        self.logger = logger
        self.base_ref = base_ref
        self.deployment_config = load_yaml("deployment/config/deployment.yml")

    def validate(self):

        self.logger.info("Starting Repository Validation...")

        ProjectStructureValidator(self.logger).validate()
        DbtOwnedObjectsValidator(self.logger, root_folder="snowflake").validate()
        DbtProjectValidator(self.logger, self.deployment_config).validate()

        root_folder = self.deployment_config["schemachange"]["root_folder"]
        deployment_order = self.deployment_config["deployment_order"]

        SchemaPathValidator(
            self.logger,
            root_folder,
            deployment_order,
        ).validate()

        VersionFormatValidator(self.logger, root_folder).validate()

        HardcodedDatabaseRefValidator(self.logger, root_folder).validate()

        HardcodedWarehouseRefValidator(self.logger, root_folder).validate()

        WarehousesConfigValidator(
            self.logger,
            self.deployment_config,
            root_folder=root_folder,
        ).validate()

        DuplicateVersionValidator(self.logger, root_folder).validate()

        GrantRolesValidator(
            self.logger,
            self.deployment_config,
            root_folder=root_folder,
        ).validate()

        ImmutableMigrationValidator(
            self.logger,
            base_ref=self.base_ref,
            root_folder=root_folder,
        ).validate()

        self.logger.info("All Repository Validations Completed Successfully.")
