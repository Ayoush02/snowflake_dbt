"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Validate Git repo paths and warehouse access before Streamlit deploy.
"""

from pathlib import Path

from jinja2 import Environment


class StreamlitPreflight:
    """Run Snowflake checks that SchemaChange does not surface clearly on failure."""

    def __init__(self, snowflake_connection, logger, deployment_config, environment):
        self.snowflake = snowflake_connection
        self.logger = logger
        self.deployment_config = deployment_config
        self.environment = environment

    def validate(
        self,
        schemachange_vars: dict,
        database: str,
        schema: str,
        root_folder: str,
    ) -> None:
        """Validate prerequisites for Streamlit Git deploy."""

        git_repo = schemachange_vars["git_repository"]
        git_branch = schemachange_vars["git_branch"]
        app_root = self._resolve_app_root(root_folder)
        git_path = f"@{git_repo}/branches/{git_branch}/{app_root}/"
        query_warehouse = schemachange_vars["warehouses"]["DEVELOPER"]

        self.logger.info(
            f"Streamlit preflight: validating Git path and warehouse for "
            f"{database}.{schema}"
        )

        self._use_target_context(database, schema)
        self._validate_git_path(git_path)
        self._validate_warehouse(query_warehouse)

    def _resolve_app_root(self, streamlit_sql_folder: str) -> str:
        """
        Map snowflake/streamlit/<layer>/<schema> to the matching streamlit_apps folder.
        """

        sql_path = Path(streamlit_sql_folder)
        layer = sql_path.parts[-2]
        schema = sql_path.parts[-1]
        apps_parent = Path("snowflake/streamlit_apps") / layer / schema

        if not apps_parent.is_dir():
            raise RuntimeError(
                f"No streamlit_apps folder found for Streamlit target: {apps_parent}"
            )

        app_dirs = sorted(path for path in apps_parent.iterdir() if path.is_dir())

        if len(app_dirs) != 1:
            app_names = [path.name for path in app_dirs]
            raise RuntimeError(
                f"Expected exactly one Streamlit app folder under {apps_parent}, "
                f"found {len(app_dirs)}: {app_names}"
            )

        app_dir = app_dirs[0]
        return str(app_dir).replace("\\", "/")

    def validate_rendered_scripts(
        self,
        root_folder: str,
        schemachange_vars: dict,
        database: str,
        schema: str,
    ) -> None:
        """Re-run rendered Streamlit SQL statement-by-statement for diagnostics."""

        jinja_env = Environment()
        root_path = Path(root_folder)

        self.logger.error("Diagnosing Streamlit SQL failures statement-by-statement:")
        self._use_target_context(database, schema)

        for sql_file in sorted(root_path.glob("*.sql")):
            rendered = jinja_env.from_string(
                sql_file.read_text(encoding="utf-8")
            ).render(**schemachange_vars)

            for statement in self._split_statements(rendered):
                preview = " ".join(statement.split())
                if len(preview) > 180:
                    preview = preview[:177] + "..."

                self.logger.error(f"Executing {sql_file.name}: {preview}")
                self.snowflake.execute(statement)

    def _use_target_context(self, database: str, schema: str) -> None:
        self.snowflake.execute(f"USE DATABASE {database}")
        self.snowflake.execute(f"USE SCHEMA {schema}")

    def _validate_git_path(self, git_path: str) -> None:
        list_sql = f"LIST {git_path};"
        self.logger.info(f"Streamlit preflight LIST: {list_sql}")

        rows = self.snowflake.execute(list_sql)

        if not rows:
            raise RuntimeError(
                f"Streamlit Git path is empty or missing: {git_path}. "
                "Confirm streamlit_apps files exist on the configured branch and "
                "CICD_DEPLOY_ROLE has READ on the Git repository."
            )

        file_names = [row[0] for row in rows]
        self.logger.info(
            f"Streamlit preflight found {len(file_names)} file(s) at Git path."
        )

        if not any(name.endswith("streamlit_app.py") for name in file_names):
            raise RuntimeError(
                f"streamlit_app.py not found under Git path: {git_path}. "
                f"Files seen: {file_names}"
            )

    def _validate_warehouse(self, warehouse_name: str) -> None:
        show_sql = f"SHOW WAREHOUSES LIKE '{warehouse_name}';"
        self.logger.info(f"Streamlit preflight: {show_sql}")

        rows = self.snowflake.execute(show_sql)

        if not rows:
            raise RuntimeError(
                f"Query warehouse '{warehouse_name}' does not exist in Snowflake. "
                "Create the warehouse or update deployment/config/deployment.yml."
            )

        self.logger.info(
            f"Streamlit preflight: warehouse '{warehouse_name}' exists."
        )

    @staticmethod
    def _split_statements(sql: str) -> list[str]:
        statements = []
        buffer: list[str] = []

        for line in sql.splitlines():
            stripped = line.strip()

            if not stripped or stripped.startswith("--"):
                continue

            buffer.append(line)

            if stripped.endswith(";"):
                statement = "\n".join(buffer).strip()
                if statement:
                    statements.append(statement)
                buffer = []

        trailing = "\n".join(buffer).strip()
        if trailing:
            statements.append(trailing)

        return statements
