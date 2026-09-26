"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Shared helpers for SchemaChange migration version numbers.
"""

from __future__ import annotations

import re
from pathlib import Path

VERSIONED_FILENAME_PATTERN = re.compile(
    r"^V(?P<version>\d+\.\d+\.\d+)__(?P<description>.+)\.sql$",
    re.IGNORECASE,
)

PLACEHOLDER_FILENAME_PATTERN = re.compile(
    r"^V__(?P<description>.+)\.sql$",
    re.IGNORECASE,
)

REPEATABLE_FILENAME_PATTERN = re.compile(
    r"^R__(?P<description>.+)\.sql$",
    re.IGNORECASE,
)


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse a dotted version string into numeric components."""

    parts = version.split(".")

    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Invalid migration version: {version}")

    return int(parts[0]), int(parts[1]), int(parts[2])


def format_version(version: tuple[int, int, int]) -> str:
    """Format numeric version components as V<major>.<minor>.<patch>."""

    return f"V{version[0]}.{version[1]}.{version[2]}"


def versioned_filename(version: tuple[int, int, int], description: str) -> str:
    """Build a versioned migration filename."""

    return f"{format_version(version)}__{description}.sql"


def compare_versions(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
) -> int:
    """Compare two version tuples. Returns -1, 0, or 1."""

    if left < right:
        return -1

    if left > right:
        return 1

    return 0


def max_version(versions: list[tuple[int, int, int]]) -> tuple[int, int, int] | None:
    """Return the highest version from a list, or None when empty."""

    if not versions:
        return None

    return max(versions)


def extract_version_from_filename(filename: str) -> tuple[int, int, int] | None:
    """Return version tuple when filename is versioned, else None."""

    match = VERSIONED_FILENAME_PATTERN.match(filename)

    if not match:
        return None

    return parse_version(match.group("version"))


def is_placeholder_filename(filename: str) -> bool:
    """Return True when the filename uses the V__ placeholder convention."""

    return bool(PLACEHOLDER_FILENAME_PATTERN.match(filename))


def is_versioned_filename(filename: str) -> bool:
    """Return True when the filename contains an explicit version number."""

    return bool(VERSIONED_FILENAME_PATTERN.match(filename))


def is_repeatable_filename(filename: str) -> bool:
    """Return True when the filename is a repeatable migration."""

    return bool(REPEATABLE_FILENAME_PATTERN.match(filename))


def next_version_for_description(
    current_max: tuple[int, int, int] | None,
    description: str,
    default_version: tuple[int, int, int],
) -> tuple[int, int, int]:
    """
    Compute the next version for a placeholder migration in one schema folder.

    create_* descriptions bump the table sequence (middle digit).
    All other descriptions bump the change sequence (patch digit).
    """

    if current_max is None:
        return default_version

    major, minor, patch = current_max
    normalized_description = description.lower()

    if normalized_description.startswith("create_"):
        return major, minor + 1, 0

    return major, minor, patch + 1


def schema_folder_key(folder: Path) -> tuple[str, str] | None:
    """
    Return (database_layer, schema) for a migration folder path.

    Expected layout: snowflake/<object_type>/<database>/<schema>/file.sql
    """

    parts = folder.parts

    if len(parts) < 4:
        return None

    database_layer = parts[-2].upper()
    schema = parts[-1].upper()
    return database_layer, schema


def collect_versions_in_folder(folder: Path) -> list[tuple[int, int, int]]:
    """Return explicit version numbers found in one migration folder."""

    versions = []

    if not folder.is_dir():
        return versions

    for sql_file in folder.glob("*.sql"):
        version = extract_version_from_filename(sql_file.name)

        if version is not None:
            versions.append(version)

    return versions


def collect_versions_in_tree(root_folder: Path) -> list[tuple[int, int, int]]:
    """Return all explicit version numbers found anywhere under root_folder."""

    versions = []

    if not root_folder.is_dir():
        return versions

    for sql_file in root_folder.rglob("*.sql"):
        version = extract_version_from_filename(sql_file.name)

        if version is not None:
            versions.append(version)

    return versions
