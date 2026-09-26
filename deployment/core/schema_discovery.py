"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Discover database/schema targets from the repository folder structure.

Folder convention:
    snowflake/<object_type>/<database>/<schema>/...
    snowflake/snowpark/<database>/<schema>/<procedure>/...
    snowflake/streamlit/<database>/<schema>/*.sql
    snowflake/streamlit_apps/<database>/<schema>/<app_name>/...
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, order=True)
class SchemaTarget:
    """A Snowflake database/schema pair derived from folder names."""

    database_layer: str
    schema: str

    def snowflake_database(self, environment: str) -> str:
        return f"{environment}_{self.database_layer}"


class SchemaDiscovery:
    """Scan the repository and build deployment targets."""

    OBJECT_TYPES_WITH_SCHEMA = {
        "file_formats",
        "stages",
        "streams",
        "functions",
        "storedprocedures",
        "dynamic_tables",
        "tasks",
        "pipes",
        "grants",
        "streamlit",
    }

    def __init__(self, root_folder: str, deployment_order: list[str]):
        self.root_folder = Path(root_folder)
        self.deployment_order = deployment_order

    def discover_targets(self) -> list[SchemaTarget]:
        """Return sorted unique database/schema pairs found in the repo."""

        targets: set[SchemaTarget] = set()

        if not self.root_folder.exists():
            return []

        for object_type in self.deployment_order:
            object_type_path = self.root_folder / object_type

            if not object_type_path.is_dir():
                continue

            if object_type == "snowpark":
                targets.update(self._discover_snowpark_targets(object_type_path))
                continue

            if object_type == "streamlit_apps":
                targets.update(
                    self._discover_streamlit_apps_targets(object_type_path)
                )
                continue

            if object_type not in self.OBJECT_TYPES_WITH_SCHEMA:
                continue

            for database_path in sorted(object_type_path.iterdir()):
                if not database_path.is_dir():
                    continue

                for schema_path in sorted(database_path.iterdir()):
                    if schema_path.is_dir():
                        targets.add(
                            SchemaTarget(
                                database_layer=database_path.name.upper(),
                                schema=schema_path.name.upper(),
                            )
                        )

        return self.sort_targets(sorted(targets))

    def sort_targets(self, targets: list[SchemaTarget]) -> list[SchemaTarget]:
        """
        Order targets RAW -> TRANSFORM -> CONSUMPTION, then schema name.

        Default dataclass ordering is alphabetical on layer name, which deploys
        CONSUMPTION (Streamlit) before RAW (tables) and can block the pipeline.
        """

        layer_rank = {
            "RAW": 0,
            "TRANSFORM": 1,
            "CONSUMPTION": 2,
        }

        return sorted(
            targets,
            key=lambda target: (
                layer_rank.get(target.database_layer, 99),
                target.schema,
            ),
        )

    def deployment_roots(
        self,
        target: SchemaTarget,
        object_type: str,
    ) -> list[Path]:
        """Return root folders to deploy for one target and object type."""

        if object_type == "snowpark":
            snowpark_root = (
                self.root_folder
                / "snowpark"
                / target.database_layer
                / target.schema
            )

            if not snowpark_root.is_dir():
                return []

            return sorted(
                path
                for path in snowpark_root.iterdir()
                if path.is_dir() and self._has_sql_files(path)
            )

        if object_type == "streamlit_apps":
            return []

        root = (
            self.root_folder
            / object_type
            / target.database_layer
            / target.schema
        )

        if root.is_dir() and self._has_sql_files(root):
            return [root]

        return []

    @staticmethod
    def _discover_snowpark_targets(snowpark_root: Path) -> set[SchemaTarget]:
        targets: set[SchemaTarget] = set()

        for database_path in sorted(snowpark_root.iterdir()):
            if not database_path.is_dir():
                continue

            for schema_path in sorted(database_path.iterdir()):
                if schema_path.is_dir():
                    targets.add(
                        SchemaTarget(
                            database_layer=database_path.name.upper(),
                            schema=schema_path.name.upper(),
                        )
                    )

        return targets

    @staticmethod
    def _discover_streamlit_apps_targets(
        streamlit_apps_root: Path,
    ) -> set[SchemaTarget]:
        """Discover DB/schema targets from streamlit_apps/ folder tree."""

        targets: set[SchemaTarget] = set()

        for database_path in sorted(streamlit_apps_root.iterdir()):
            if not database_path.is_dir():
                continue

            for schema_path in sorted(database_path.iterdir()):
                if schema_path.is_dir():
                    targets.add(
                        SchemaTarget(
                            database_layer=database_path.name.upper(),
                            schema=schema_path.name.upper(),
                        )
                    )

        return targets

    @staticmethod
    def _has_sql_files(folder: Path) -> bool:
        return any(folder.rglob("*.sql"))
