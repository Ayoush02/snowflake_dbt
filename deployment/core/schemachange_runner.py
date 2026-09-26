"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Execute SchemaChange per database/schema folder target.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from jinja2 import Environment

from deployment.core.jinja_vars import (
    build_access_roles_for_target,
    build_databases,
    build_dbt_vars,
    build_warehouses,
    default_grant_privilege,
    get_database_layers,
)
from deployment.core.schema_discovery import SchemaDiscovery


def _schemachange_executable() -> str:
    """Return the schemachange CLI path installed in the current environment."""

    executable = shutil.which("schemachange")

    if executable:
        return executable

    venv_executable = Path(sys.executable).parent / "schemachange"

    if venv_executable.exists():
        return str(venv_executable)

    raise RuntimeError(
        "schemachange CLI not found. Install requirements.txt before deploying."
    )


class SchemaChangeRunner:
    """Run schemachange deploy for each discovered schema target."""

    CONNECTIONS_FILE = "connections.toml"
    CONNECTION_NAME = "cicd"

    GIT_DEPENDENT_OBJECT_TYPES = frozenset({"storedprocedures", "snowpark", "streamlit"})

    # Object types whose SQL can SELECT from tables that *dbt* owns (dbt
    # creates/materializes everything under RAW/TRANSFORM/CONSUMPTION - see
    # the "tables/ and views/ are intentionally omitted" note in
    # deployment.yml). If one of these is deployed before dbt has run, the
    # underlying table may not exist yet and the deploy fails.
    #
    # Kept here in code (not in deployment.yml) on purpose: this is a code-level
    # ordering constraint about *how* deploy.py sequences dbt vs. SchemaChange,
    # not a per-environment setting someone should tune from the config file.
    #
    # Currently only "dynamic_tables" is empty/unused in this repo, but the
    # moment real dynamic tables are added that read dbt-built tables, this
    # is what keeps that safe. Add an object type here if it ever needs to
    # read a dbt-owned table.
    POST_DBT_OBJECT_TYPES = frozenset({"dynamic_tables"})

    def __init__(
        self,
        deployment_config,
        schemachange_config,
        logger,
        environment,
        dry_run=False,
        git_refetch_callback=None,
    ):
        self.deployment_config = deployment_config
        self.schemachange_config = schemachange_config
        self.logger = logger
        self.environment = environment
        self.dry_run = dry_run
        self.git_refetch_callback = git_refetch_callback
        self.connections_file = None

    def execute(self, object_types=None):
        """
        Deploy all pending migrations grouped by folder-derived database/schema.

        object_types: optional iterable restricting this run to a subset of
        deployment_order (e.g. only the object types that must run before, or
        only the ones that must run after, dbt). None (the default) deploys
        every object type, in one pass, as before.
        """

        self.connections_file = self._write_connections_toml()

        try:
            self._execute_deployments(object_types=object_types)
        finally:
            if self.connections_file and self.connections_file.exists():
                self.connections_file.unlink()

    def _execute_deployments(self, object_types=None):
        """Run schemachange for all discovered schema targets."""

        history_table = self._history_table()
        deployment_order = self.deployment_config["deployment_order"]

        # Narrow to the requested object types, but keep the config's own
        # ordering - object_types only decides *which* types run in this
        # call, never the relative order between them.
        if object_types is not None:
            deployment_order = [
                object_type
                for object_type in deployment_order
                if object_type in object_types
            ]

        root_folder = self.deployment_config["schemachange"]["root_folder"]

        discovery = SchemaDiscovery(root_folder, deployment_order)
        targets = discovery.discover_targets()

        if not targets:
            self.logger.warning(
                "No database/schema targets with SQL files were discovered."
            )
            return

        self.logger.info(
            f"Discovered {len(targets)} database/schema target(s) for deployment."
        )
        self._log_deploy_plan(discovery, targets)

        create_history_table = self.deployment_config["schemachange"].get(
            "create_change_history_table",
            True,
        )

        history_created = False
        total_runs = 0

        for target in targets:
            database = target.snowflake_database(self.environment)

            self.logger.info(
                f"Deploying target: {database}.{target.schema}"
            )

            for object_type in deployment_order:
                roots = discovery.deployment_roots(target, object_type)

                for root_folder_path in roots:
                    self._run_schemachange(
                        root_folder=str(root_folder_path),
                        database=database,
                        schema=target.schema,
                        database_layer=target.database_layer,
                        history_table=history_table,
                        create_history_table=(
                            create_history_table and not history_created
                        ),
                        object_type=object_type,
                    )
                    history_created = True
                    total_runs += 1

        if total_runs == 0:
            self.logger.warning(
                "No SQL migration folders were found for deployment."
            )
            return

        self.logger.info(
            f"SchemaChange completed successfully across {total_runs} folder(s)."
        )

    def _log_deploy_plan(self, discovery: SchemaDiscovery, targets) -> None:
        """Log the resolved deploy order so CI logs show what runs before Streamlit."""

        for target in targets:
            database = target.snowflake_database(self.environment)
            for object_type in self.deployment_config["deployment_order"]:
                for root_folder_path in discovery.deployment_roots(
                    target,
                    object_type,
                ):
                    self.logger.info(
                        f"Deploy plan: [{object_type}] "
                        f"{database}.{target.schema} -> {root_folder_path}"
                    )

    def _history_table(self) -> str:
        history_tables = self.deployment_config["schemachange"]["history_table"]

        if self.environment not in history_tables:
            raise ValueError(
                f"No change history table configured for environment: "
                f"{self.environment}"
            )

        return history_tables[self.environment]

    def _git_branch(self) -> str:
        branch_map = self.deployment_config.get("git", {}).get(
            "branch",
            {"DEV": "dev", "PROD": "main"},
        )

        if self.environment not in branch_map:
            raise ValueError(
                f"No Git branch configured for environment: {self.environment}"
            )

        return branch_map[self.environment]

    def _schemachange_vars(self, database_layer=None, schema=None) -> dict:
        git_config = self.deployment_config.get("git", {})

        database_layers = get_database_layers(self.deployment_config)
        databases = build_databases(self.environment, database_layers)
        warehouses = build_warehouses(self.environment, self.deployment_config)

        access_roles = {}
        grant_role = ""
        access_role = ""

        if database_layer and schema:
            access_roles = build_access_roles_for_target(
                self.environment,
                database_layer,
                schema,
                self.deployment_config,
            )
            default_privilege = default_grant_privilege(self.deployment_config)
            grant_role = access_roles[default_privilege]
            access_role = grant_role

        vars_payload = {
            "git_repository": git_config["repository_name"],
            "git_branch": self._git_branch(),
            "environment": self.environment,
            "grant_role": grant_role,
            "access_role": access_role,
            "access_roles": access_roles,
            "databases": databases,
            "warehouses": warehouses,
        }
        vars_payload.update(build_dbt_vars(self.environment, self.deployment_config))
        return vars_payload

    def _write_connections_toml(self) -> Path:
        """Write a Snowflake connections file for schemachange 4.x."""

        snowflake_settings = self.deployment_config["snowflake"]
        connections_path = Path(self.CONNECTIONS_FILE)
        passphrase = snowflake_settings.get("private_key_passphrase", "")
        passphrase = passphrase.strip() if isinstance(passphrase, str) else ""

        lines = [
            f"[{self.CONNECTION_NAME}]",
            f'account = "{snowflake_settings["account"]}"',
            f'user = "{snowflake_settings["user"]}"',
            f'role = "{snowflake_settings["role"]}"',
            f'warehouse = "{snowflake_settings["warehouse"]}"',
            'authenticator = "snowflake_jwt"',
            f'private_key_file = "{snowflake_settings["private_key_path"]}"',
        ]

        if passphrase:
            lines.append(f'private_key_file_pwd = "{passphrase}"')

        connections_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        connections_path.chmod(0o600)

        self.logger.info(
            f"Created SchemaChange connections file: {connections_path}"
        )

        return connections_path

    def _build_subprocess_env(self, database, schema, snowflake_settings):
        """Build environment variables for the schemachange subprocess."""

        env = os.environ.copy()
        env.update(
            {
                "SNOWFLAKE_ACCOUNT": snowflake_settings["account"],
                "SNOWFLAKE_USER": snowflake_settings["user"],
                "SNOWFLAKE_ROLE": snowflake_settings["role"],
                "SNOWFLAKE_WAREHOUSE": snowflake_settings["warehouse"],
                "SNOWFLAKE_DATABASE": database,
                "SNOWFLAKE_SCHEMA": schema,
                "SNOWFLAKE_AUTHENTICATOR": "snowflake_jwt",
                "SNOWFLAKE_PRIVATE_KEY_FILE": snowflake_settings[
                    "private_key_path"
                ],
            }
        )

        passphrase = snowflake_settings.get("private_key_passphrase", "")
        passphrase = passphrase.strip() if isinstance(passphrase, str) else ""

        if passphrase:
            env["SNOWFLAKE_PRIVATE_KEY_FILE_PWD"] = passphrase

        return env

    def _run_schemachange(
        self,
        root_folder,
        database,
        schema,
        database_layer,
        history_table,
        create_history_table,
        object_type,
    ):
        schemachange_settings = self.deployment_config["schemachange"]
        snowflake_settings = self.deployment_config["snowflake"]

        schemachange_vars = self._schemachange_vars(database_layer, schema)

        log_level = self.schemachange_config.get("log_level", "INFO")
        if object_type == "streamlit":
            log_level = "DEBUG"

        command = [
            _schemachange_executable(),
            "deploy",
            "--config-folder",
            "deployment/config",
            "-f",
            root_folder,
            "-c",
            history_table,
            "-d",
            database,
            "-s",
            schema,
            "-V",
            json.dumps(schemachange_vars),
            "-C",
            self.CONNECTION_NAME,
            "--schemachange-connections-file-path",
            str(self.connections_file),
            "-L",
            log_level,
        ]

        self.logger.info(
            f"SchemaChange vars: git_branch={schemachange_vars['git_branch']}, "
            f"git_repository={schemachange_vars['git_repository']}, "
            f"environment={schemachange_vars['environment']}, "
            f"grant_role={schemachange_vars['grant_role']}, "
            f"access_roles={schemachange_vars['access_roles']}, "
            f"databases={schemachange_vars['databases']}, "
            f"warehouses={schemachange_vars['warehouses']}"
        )

        if schemachange_settings.get("autocommit", True):
            command.append("-ac")

        if create_history_table:
            command.append("--create-change-history-table")

        if self.dry_run:
            command.append("--dry-run")

        version_regex = self.schemachange_config.get(
            "version_number_validation_regex"
        )
        if version_regex:
            command.extend(
                ["--version-number-validation-regex", version_regex]
            )

        if (
            object_type in self.GIT_DEPENDENT_OBJECT_TYPES
            and self.git_refetch_callback is not None
        ):
            self.logger.info(
                f"Refreshing Snowflake Git Repository before {object_type} deploy."
            )
            self.git_refetch_callback()

        if object_type == "streamlit" and not self.dry_run:
            self._run_streamlit_preflight(
                schemachange_vars,
                database,
                schema,
                root_folder,
            )

        self.logger.info(
            f"Running SchemaChange for {object_type}: "
            f"{database}.{schema} -> {root_folder}"
        )

        env = self._build_subprocess_env(database, schema, snowflake_settings)

        result = subprocess.run(
            command,
            text=True,
            env=env,
            capture_output=True,
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                self.logger.info(line)

        if result.returncode != 0:
            if result.stderr:
                for line in result.stderr.splitlines():
                    self.logger.error(line)

            if result.stdout:
                stdout_lines = result.stdout.splitlines()
                for line in stdout_lines:
                    lowered = line.lower()
                    if (
                        "error" in lowered
                        or "compilation" in lowered
                        or "failed to execute" in lowered
                        or "002043" in lowered
                        or "does not exist" in lowered
                    ):
                        self.logger.error(line)

                self.logger.error(
                    "SchemaChange output (last 25 lines):"
                )
                for line in stdout_lines[-25:]:
                    self.logger.error(line)

            self._log_rendered_scripts(root_folder, schemachange_vars)

            if object_type == "streamlit" and not self.dry_run:
                self._diagnose_streamlit_failure(
                    root_folder,
                    schemachange_vars,
                    database,
                    schema,
                )

            raise RuntimeError(
                f"SchemaChange failed for {database}.{schema} "
                f"({object_type}) in {root_folder}. "
                "Review SchemaChange error lines above for the Snowflake SQL error."
            )

    def _log_rendered_scripts(self, root_folder: str, schemachange_vars: dict) -> None:
        """Log Jinja-rendered SQL from the failed folder to surface Snowflake errors in CI."""

        jinja_env = Environment()
        root_path = Path(root_folder)

        for sql_file in sorted(root_path.glob("*.sql")):
            try:
                rendered = jinja_env.from_string(
                    sql_file.read_text(encoding="utf-8")
                ).render(**schemachange_vars)
            except Exception as exc:
                self.logger.error(
                    f"Could not render {sql_file.name} for diagnostics: {exc}"
                )
                continue

            self.logger.error(f"Rendered SQL for {sql_file.name}:")
            for line in rendered.splitlines():
                self.logger.error(line)

    def _run_streamlit_preflight(
        self,
        schemachange_vars: dict,
        database: str,
        schema: str,
        root_folder: str,
    ) -> None:
        from deployment.core.snowflake_connection import SnowflakeConnection
        from deployment.core.streamlit_preflight import StreamlitPreflight

        snowflake = SnowflakeConnection(self.deployment_config, self.logger)

        try:
            snowflake.connect()
            StreamlitPreflight(
                snowflake,
                self.logger,
                self.deployment_config,
                self.environment,
            ).validate(schemachange_vars, database, schema, root_folder)
        finally:
            snowflake.close()

    def _diagnose_streamlit_failure(
        self,
        root_folder: str,
        schemachange_vars: dict,
        database: str,
        schema: str,
    ) -> None:
        from deployment.core.snowflake_connection import SnowflakeConnection
        from deployment.core.streamlit_preflight import StreamlitPreflight

        snowflake = SnowflakeConnection(self.deployment_config, self.logger)

        try:
            snowflake.connect()
            StreamlitPreflight(
                snowflake,
                self.logger,
                self.deployment_config,
                self.environment,
            ).validate_rendered_scripts(
                root_folder,
                schemachange_vars,
                database,
                schema,
            )
        except Exception as exc:
            self.logger.error(f"Streamlit diagnostic execution failed: {exc}")
        finally:
            snowflake.close()
