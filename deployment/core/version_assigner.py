"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Assign explicit version numbers to V__ placeholder migration files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from deployment.core.migration_versions import (
    PLACEHOLDER_FILENAME_PATTERN,
    collect_versions_in_tree,
    format_version,
    max_version,
    next_version_for_description,
    parse_version,
    schema_folder_key,
    versioned_filename,
)


@dataclass(frozen=True)
class VersionAssignment:
    """One placeholder rename operation."""

    source_path: Path
    target_path: Path
    assigned_version: tuple[int, int, int]


class VersionAssigner:
    """
    Rename V__*.sql files to the next repo-wide version number.

    SchemaChange uses one global change-history table, so assigned versions
    must always be higher than the current maximum anywhere in the repo.
    """

    DEFAULT_VERSION_PREFIX = (1, 0, 0)

    def __init__(self, logger, deployment_config, dry_run: bool = False):
        self.logger = logger
        self.deployment_config = deployment_config
        self.dry_run = dry_run
        self.root_folder = Path(
            deployment_config["schemachange"]["root_folder"]
        )
        self.version_prefixes = self._load_version_prefixes()

    def assign(self) -> list[VersionAssignment]:
        """Assign versions to all placeholder files and return rename operations."""

        placeholders = self._discover_placeholders()

        if not placeholders:
            self.logger.info("No V__ placeholder migration files found.")
            return []

        self.logger.info(
            f"Found {len(placeholders)} placeholder migration file(s) to assign."
        )

        repo_max = max_version(collect_versions_in_tree(self.root_folder))
        running_max = repo_max
        assignments: list[VersionAssignment] = []
        assigned_versions: set[tuple[int, int, int]] = set()

        for placeholder_path in placeholders:
            assignment = self._assign_placeholder(
                placeholder_path,
                running_max,
                assigned_versions,
            )
            assignments.append(assignment)
            assigned_versions.add(assignment.assigned_version)
            running_max = assignment.assigned_version

        if assignments and not self.dry_run:
            self._apply_assignments(assignments)

        return assignments

    def _discover_placeholders(self) -> list[Path]:
        placeholders = []

        for sql_file in sorted(self.root_folder.rglob("*.sql")):
            if PLACEHOLDER_FILENAME_PATTERN.match(sql_file.name):
                placeholders.append(sql_file)

        return placeholders

    def _assign_placeholder(
        self,
        placeholder_path: Path,
        running_max: tuple[int, int, int] | None,
        assigned_versions: set[tuple[int, int, int]],
    ) -> VersionAssignment:
        match = PLACEHOLDER_FILENAME_PATTERN.match(placeholder_path.name)
        description = match.group("description")
        default_version = self._default_version_for_schema(
            schema_folder_key(placeholder_path.parent)
        )

        next_version = next_version_for_description(
            running_max,
            description,
            default_version,
        )

        while next_version in assigned_versions:
            next_version = (
                next_version[0],
                next_version[1],
                next_version[2] + 1,
            )

        target_name = versioned_filename(next_version, description)
        target_path = placeholder_path.parent / target_name

        if target_path.exists():
            raise ValueError(
                f"Cannot assign {target_name}; file already exists at {target_path}."
            )

        self.logger.info(
            f"Assigned {format_version(next_version)} -> {target_path}"
        )

        return VersionAssignment(
            source_path=placeholder_path,
            target_path=target_path,
            assigned_version=next_version,
        )

    def _default_version_for_schema(
        self,
        schema_key: tuple[str, str] | None,
    ) -> tuple[int, int, int]:
        if schema_key is None:
            return self.DEFAULT_VERSION_PREFIX

        database_layer, schema = schema_key
        configured = self.version_prefixes.get(database_layer, {}).get(schema)

        if configured:
            return parse_version(configured)

        return self.DEFAULT_VERSION_PREFIX

    def _load_version_prefixes(self) -> dict[str, dict[str, str]]:
        configured = self.deployment_config.get("version_prefixes", {})
        normalized: dict[str, dict[str, str]] = {}

        for database_layer, schema_map in configured.items():
            normalized[database_layer.upper()] = {
                schema.upper(): version
                for schema, version in schema_map.items()
            }

        return normalized

    def _apply_assignments(self, assignments: list[VersionAssignment]) -> None:
        for assignment in assignments:
            assignment.source_path.rename(assignment.target_path)
